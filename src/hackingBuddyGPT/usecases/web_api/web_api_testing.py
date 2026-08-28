"""
Merged web-API use case: detect the target surface, then pentest it.

This single use case subsumes the former ``SimpleWebAPIDocumentation`` (detection) and
``SimpleWebAPITesting`` (testing) use cases, which now serve as internal phase engines. It
runs in one of three modes:

* ``document`` – run detection only and write the discovered OpenAPI spec.
* ``test``     – skip detection; pentest a surface passed via ``--surface`` (required).
* ``auto``     – (default) if ``--surface`` is given, pentest it directly; otherwise run
                 detection to build the surface and then pentest it.

The surface passed to ``--surface`` may be an OpenAPI spec *or* a website sitemap
(``sitemap.xml``, a URL list, or an HTML page); both are normalised through
``utils.web_api.target_surface`` before the testing phase consumes them.
"""

import json
import os
import traceback
from dataclasses import field
from typing import Any

from hackingBuddyGPT.strategies import SimpleStrategy
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.usecases.web_api.simple_openapi_documentation import (
    SimpleWebAPIDocumentation,
)
from hackingBuddyGPT.usecases.web_api.simple_web_api_testing import (
    SimpleWebAPITesting,
)
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.web_api.target_surface import OpenAPISurface, load_surface

VALID_MODES = ("document", "test", "auto")


@use_case("Web API testing: detect the target surface (OpenAPI spec or sitemap), then pentest it")
class WebAPITesting(SimpleStrategy):
    config_path: str = parameter(
        desc="Configuration file path (host, token, correct_endpoints, credentials, ...)",
        default="",
    )
    strategy_string: str = parameter(desc="prompt strategy: cot | tot | icl", default="")
    mode: str = parameter(
        desc="document (detect + write spec only) | test (pentest --surface, required) | auto "
        "(default: detect then pentest, or pentest --surface directly if given)",
        default="auto",
    )
    surface: str = parameter(
        desc="Path to an OpenAPI spec or sitemap to pentest against. When set, detection is skipped.",
        default="",
    )
    detection_max_turns: int = parameter(
        desc="Maximum detection rounds when the detection phase runs.",
        default=20,
    )

    _surface_obj: Any = field(default=None, init=False)
    _detection: Any = field(default=None, init=False)
    _testing: Any = field(default=None, init=False)

    def get_name(self) -> str:
        return self.__class__.__name__

    def init(self):
        super().init()
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {'|'.join(VALID_MODES)}, got {self.mode!r}")

        host = None
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path) as config_file:
                host = json.load(config_file).get("host")

        if self.surface:
            self._surface_obj = load_surface(self.surface, host)
            if getattr(self._surface_obj, "is_sitemap", False):
                self.log.console.print(
                    "[yellow]Surface is a sitemap: no request/response schemas or documented auth "
                    "metadata are available, so schema- and security-driven tests fall back to path "
                    "heuristics (coverage is thinner than an OpenAPI-driven run).[/yellow]"
                )

        if self.mode == "test" and self._surface_obj is None:
            raise ValueError("mode=test requires --surface (an OpenAPI spec or a sitemap)")

    async def perform_round(self, turn: int):
        # SimpleStrategy requires this, but WebAPITesting overrides run() with an explicit
        # detection -> testing orchestration, so no single shared round entry point is used.
        raise NotImplementedError("WebAPITesting orchestrates its phases in run(), not perform_round()")

    async def run(self, configuration):
        self.configuration = configuration
        await self.log.start_run(self.get_name(), self.serialize_configuration(configuration))
        try:
            if self._surface_obj is None and self.mode in ("document", "auto"):
                await self._run_detection()

            if self.mode == "document":
                await self.log.run_was_success()
                return True

            await self._run_testing()
            await self.log.run_was_success()
            return True
        except Exception:
            await self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise

    async def _run_detection(self):
        """Run the detection phase; persist and hand off the discovered OpenAPI surface."""
        engine = SimpleWebAPIDocumentation(
            llm=self.llm,
            log=self.log,
            config_path=self.config_path,
            strategy_string=self.strategy_string,
        )
        engine.init()
        self._detection = engine

        turn, done = 1, False
        while turn <= self.detection_max_turns and not done:
            async with self.log.section(f"detect round {turn}"):
                self.log.console.log(f"[yellow]Detection turn {turn}/{self.detection_max_turns}")
                done = await engine.perform_round(turn)
            turn += 1

        engine._documentation_handler.write_openapi_to_yaml()
        self._surface_obj = OpenAPISurface.from_dict(engine.built_surface_document())

    async def _run_testing(self):
        """Run the testing phase against the resolved surface."""
        if self._surface_obj is None:
            raise ValueError("no surface available for the testing phase")

        engine = SimpleWebAPITesting(
            llm=self.llm,
            log=self.log,
            config_path=self.config_path,
            strategy_string=self.strategy_string,
        )
        engine._injected_surface = self._surface_obj
        engine.init()
        self._testing = engine

        turn = 1
        while turn <= self.max_turns and not engine._all_test_cases_run:
            async with self.log.section(f"test round {turn}"):
                self.log.console.log(f"[yellow]Testing turn {turn}/{self.max_turns}")
                await engine.perform_round(turn)
            turn += 1
