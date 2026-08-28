import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from hackingBuddyGPT.usecases.web_api.web_api_testing import WebAPITesting
from hackingBuddyGPT.usecases.web_api.simple_web_api_testing import SimpleWebAPITesting
from hackingBuddyGPT.utils import Console
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.logging import JsonlLogger
from hackingBuddyGPT.utils.web_api.target_surface import OpenAPISurface, SitemapSurface

TEST_FILES = os.path.join(os.path.dirname(__file__), "test_files")
CONFIG = os.path.join(TEST_FILES, "fakeapi_config.json")
OAS = os.path.join(TEST_FILES, "oas", "fakeapi_oas.json")


def _logger():
    return JsonlLogger(console=Console(), log_dir=tempfile.mkdtemp())


class TestWebAPITestingModes(unittest.TestCase):
    def _build(self, **kw):
        params = dict(llm=MagicMock(), log=_logger(), config_path=CONFIG, strategy_string="cot")
        params.update(kw)
        return WebAPITesting(**params)

    def test_invalid_mode_rejected(self):
        agent = self._build(mode="bogus")
        with self.assertRaises(ValueError):
            agent.init()

    def test_test_mode_requires_surface(self):
        agent = self._build(mode="test", surface="")
        with self.assertRaises(ValueError):
            agent.init()

    def test_surface_loaded_as_openapi(self):
        agent = self._build(mode="test", surface=OAS)
        agent.init()
        self.assertIsInstance(agent._surface_obj, OpenAPISurface)
        self.assertFalse(agent._surface_obj.is_sitemap)

    def test_auto_no_surface_runs_detection_then_testing(self):
        agent = self._build(mode="auto")
        agent.init()
        agent._run_detection = AsyncMock()
        agent._run_testing = AsyncMock()
        asyncio.run(agent.run({}))
        agent._run_detection.assert_awaited_once()
        agent._run_testing.assert_awaited_once()

    def test_auto_with_surface_skips_detection(self):
        agent = self._build(mode="auto", surface=OAS)
        agent.init()
        agent._run_detection = AsyncMock()
        agent._run_testing = AsyncMock()
        asyncio.run(agent.run({}))
        agent._run_detection.assert_not_awaited()
        agent._run_testing.assert_awaited_once()

    def test_document_mode_skips_testing(self):
        agent = self._build(mode="document")
        agent.init()
        agent._run_detection = AsyncMock()
        agent._run_testing = AsyncMock()
        asyncio.run(agent.run({}))
        agent._run_detection.assert_awaited_once()
        agent._run_testing.assert_not_awaited()

    def test_reached_limit_skips_testing_and_reports_reason(self):
        # A cost limit exhausted during detection must stop the run before testing and be
        # reported as the run's failure reason.
        limits = Limits(max_rounds=0, max_tokens=0, max_cost=0.001, max_duration=0)
        agent = self._build(mode="auto", limits=limits)
        agent.init()

        async def exhaust_budget():
            agent.limits.register_message(SimpleNamespace(total_tokens=1, cost=0.01))

        agent._run_detection = exhaust_budget
        agent._run_testing = AsyncMock()
        agent.log.run_was_failure = AsyncMock()
        agent.log.run_was_success = AsyncMock()

        asyncio.run(agent.run({}))

        agent._run_testing.assert_not_awaited()  # limit reached after detection
        agent.log.run_was_success.assert_not_awaited()
        agent.log.run_was_failure.assert_awaited_once()
        self.assertIn("cost", agent.log.run_was_failure.await_args.args[0].lower())

    def test_limits_default_never_reached_when_unset(self):
        agent = self._build(mode="auto")
        agent.init()
        self.assertIsNotNone(agent.limits)
        self.assertFalse(agent.limits.reached())


class TestSurfaceInjectionIntoTestingEngine(unittest.TestCase):
    """The testing phase engine must accept any TargetSurface, not just a config-loaded OAS."""

    def _engine(self):
        return SimpleWebAPITesting(
            llm=MagicMock(), log=_logger(), config_path=CONFIG, strategy_string="cot"
        )

    def test_injected_openapi_surface_is_used(self):
        surface = OpenAPISurface.from_file(OAS)
        engine = self._engine()
        engine._injected_surface = surface
        engine.init()
        self.assertIs(engine._openapi_specification, surface.api_data)

    def test_injected_sitemap_surface_initialises(self):
        # A sitemap-derived surface (no schemas / security metadata) must still flow through
        # PenTestingInformation and the prompt engine without error.
        surface = SitemapSurface.from_urls(
            ["https://fakeapi.example/users", "https://fakeapi.example/admin/login"],
            host="https://fakeapi.example",
        )
        engine = self._engine()
        engine._injected_surface = surface
        engine.init()
        self.assertIs(engine._openapi_specification, surface.api_data)
        self.assertIn("/users", engine._openapi_specification["paths"])


if __name__ == "__main__":
    unittest.main()
