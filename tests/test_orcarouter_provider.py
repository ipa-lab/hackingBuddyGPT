"""The named OrcaRouter provider: registry, config wiring, requests and live connectivity."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import litellm

from hackingBuddyGPT.utils.llm import LiteLLM
from hackingBuddyGPT.utils.llm_providers import (
    PROVIDER_PRESETS,
    UnknownProviderError,
    get_preset,
)
from hackingBuddyGPT.utils.orcarouter.catalog import CatalogResult, ModelInfo
from hackingBuddyGPT.utils.orcarouter.config import Origins
from hackingBuddyGPT.utils.orcarouter.credentials import (
    Credential,
    CredentialState,
    DotEnvCredentialStore,
    ReauthenticationRequired,
)
from hackingBuddyGPT.utils.orcarouter.provider import (
    BASE_URL,
    FALLBACK_DEFAULT_MODEL,
    PRESET_NAME,
    RECOMMENDED_CYBER_MODEL,
    ModelSelectionError,
    OrcaRouterProvider,
)

LIVE_MODEL = os.environ.get("ORCA_LIVE_MODEL", "deepseek/deepseek-v4.1-flash")


def _model(model_id, **kwargs):
    defaults = dict(
        id=model_id,
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"openai", "openai-response"}),
    )
    defaults.update(kwargs)
    return ModelInfo(**defaults)


class FakeCatalogClient:
    def __init__(self, models):
        self.models = models

    def fetch(self, capability="chat"):
        return CatalogResult(list(self.models), source="live", capability=capability)


class FakeProvider:
    def __init__(self):
        self.api_key = None
        self.origins = Origins.resolve(env={})
        self._credential = Credential("sk-orca-fake", "api_key")
        self.state = CredentialState()

    def set_api_key(self, value):
        self.api_key = value
        self._credential = self.state.issue(Credential(value, "api_key"))
        return self._credential

    def resolve_chat_model(self, requested=""):
        if requested not in ("", "orcarouter/fusion"):
            raise ModelSelectionError(f"{requested!r} is not offered by OrcaRouter")
        return requested or "orcarouter/fusion"

    def credential(self):
        return self._credential

    def completion_kwargs(self, model, credential=None):
        return {
            "model": f"openai/{model}",
            "api_base": self.origins.api_base,
            "api_key": (credential or self.credential()).value,
        }

    def embedding_model(self, requested=""):
        return requested or "acme/text-embed-3"

    def check_response_error(self, error):
        if getattr(error, "status_code", None) == 401:
            self.state.mark_unauthorized(self.state.generation)
            raise ReauthenticationRequired("OrcaRouter rejected this credential (HTTP 401).") from error


class FakePreset:
    def __init__(self):
        self.created = None

    def create(self, **kwargs):
        self.created = FakeProvider()
        return self.created


class TestRegistry(unittest.TestCase):
    def test_orcarouter_is_a_named_preset(self):
        preset = get_preset("orcarouter")
        self.assertEqual(preset.name, PRESET_NAME)
        self.assertEqual(preset.label, "OrcaRouter")
        self.assertEqual(preset.api_base, "https://api.orcarouter.ai/v1")
        self.assertEqual(preset.auth_base, "https://www.orcarouter.ai")
        self.assertIn("ORCAROUTER", preset.env_key)
        self.assertTrue(preset.supports_pkce)
        self.assertEqual(preset.default_model, FALLBACK_DEFAULT_MODEL)
        self.assertEqual(set(PROVIDER_PRESETS), {"orcarouter"})

    def test_unknown_preset_is_rejected(self):
        with self.assertRaises(UnknownProviderError):
            get_preset("nope")

    def test_recommended_cyber_model_is_named(self):
        self.assertEqual(RECOMMENDED_CYBER_MODEL, "orcacyber-zero")

    def test_docs_row_points_at_the_public_endpoint(self):
        provider = OrcaRouterProvider(env={})
        self.assertIn(BASE_URL, provider.docs_table_row())
        self.assertIn("orcarouter", provider.docs_table_row())


class TestConfigSurface(unittest.TestCase):
    def test_llm_has_a_preset_parameter(self):
        from hackingBuddyGPT.utils.configurable import parameter_definitions_for_class

        definitions = parameter_definitions_for_class(LiteLLM, ["llm"], {})
        self.assertIn("preset", definitions)
        self.assertIn("preset_credential", definitions)


class TestLiteLLMWiring(unittest.TestCase):
    def setUp(self):
        self.preset = FakePreset()

    def _llm(self, **kwargs):
        defaults = dict(api_key="sk-orca-fake", model="orcarouter/fusion", context_size=8192, preset="orcarouter")
        defaults.update(kwargs)
        llm = LiteLLM(**defaults)
        with patch("hackingBuddyGPT.utils.llm.get_preset", return_value=self.preset):
            llm.init()
        return llm

    def test_init_selects_the_named_provider(self):
        llm = self._llm()
        self.assertIs(llm._preset_provider, self.preset.created)
        self.assertEqual(llm.model, "orcarouter/fusion")

    def test_request_goes_to_the_api_origin_with_bearer_key(self):
        llm = self._llm()
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            raise SystemExit("stop")

        with patch("hackingBuddyGPT.utils.llm.litellm.completion", side_effect=fake_completion):
            with self.assertRaises(SystemExit):
                llm.raw_completion([{"role": "user", "content": "hi"}])

        self.assertEqual(captured["api_base"], "https://api.orcarouter.ai/v1")
        self.assertEqual(captured["model"], "openai/orcarouter/fusion")
        self.assertEqual(captured["api_key"], "sk-orca-fake")
        self.assertNotIn("api.orcarouter.ai/api/v1/auth", captured["api_base"])

    def test_model_outside_the_catalog_is_refused(self):
        with self.assertRaises(ModelSelectionError):
            self._llm(model="acme/not-offered")

    def test_unknown_preset_is_refused(self):
        llm = LiteLLM(api_key="k", model="gpt-4o", context_size=8192, preset="mystery")
        with self.assertRaises(UnknownProviderError):
            llm.init()

    def test_401_is_terminal_reauth_not_a_retry(self):
        llm = self._llm()

        class Unauthorized(Exception):
            status_code = 401

        with patch("hackingBuddyGPT.utils.llm.litellm.completion", side_effect=Unauthorized("401")):
            with self.assertRaises(ReauthenticationRequired) as ctx:
                llm.raw_completion([{"role": "user", "content": "hi"}])
        self.assertIn("401", str(ctx.exception))
        self.assertTrue(llm._preset_provider.state.needs_reauth)

    def test_embedding_config_uses_the_provider_endpoint(self):
        llm = self._llm()
        config = llm.embedding_config()
        self.assertEqual(config["model"], "acme/text-embed-3")
        self.assertEqual(config["base_url"], "https://api.orcarouter.ai/v1")
        self.assertEqual(config["api_key"], "sk-orca-fake")

    def test_plain_litellm_path_is_unchanged(self):
        llm = LiteLLM(api_key="k", model="gpt-4o", context_size=8192)
        llm.init()
        self.assertIsNone(llm._preset_provider)
        self.assertEqual(llm.embedding_config(), {"model": "text-embedding-3-large", "api_key": "k"})


class TestBenchmarkProvider(unittest.TestCase):
    def test_orcarouter_is_a_benchmark_provider_choice(self):
        import benchmark_privesc as benchmark

        self.assertIn("orcarouter", benchmark.DEFAULT_MODELS)
        args = benchmark.parse_args(["--provider", "orcarouter", "--api-key", "sk-orca-test"])
        self.assertEqual(args.model, "orcarouter/fusion")

        class Container:
            port = 2222
            hostname = "target"
            image = "privesc_01_box"

        argv = benchmark.build_wintermute_argv(args, Container(), Path("/tmp/traces"), "tag")
        self.assertIn("--llm.preset=orcarouter", argv)
        self.assertIn("--llm.model=orcarouter/fusion", argv)

    def test_orcarouter_requires_a_key(self):
        import benchmark_privesc as benchmark

        with patch.dict(os.environ, {"ORCAROUTER_API_KEY": "", "ORCA_KEY": ""}, clear=False):
            with self.assertRaises(SystemExit):
                benchmark.parse_args(["--provider", "orcarouter"])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_file = str(Path(self.tmp.name) / ".env")

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_authentication_entries_are_discoverable(self):
        from hackingBuddyGPT.cli.orcarouter import _build_parser

        parser = _build_parser()
        help_text = parser.format_help()
        self.assertIn("login", help_text)
        self.assertIn("models", help_text)
        login_help = parser._subparsers._group_actions[0].choices["login"].format_help()
        self.assertIn("--api-key", login_help)
        self.assertIn("--oob", login_help)

    def test_api_key_login_stores_the_key(self):
        from hackingBuddyGPT.cli import orcarouter as cli

        with patch("hackingBuddyGPT.cli.orcarouter.getpass.getpass", return_value="sk-orca-pasted"):
            code = cli.main(["login", "--api-key", "--env-file", self.env_file])
        self.assertEqual(code, 0)
        self.assertEqual(DotEnvCredentialStore(self.env_file).load(), "sk-orca-pasted")

    def test_logout_removes_the_key(self):
        from hackingBuddyGPT.cli import orcarouter as cli

        DotEnvCredentialStore(self.env_file).save("sk-orca-pasted")
        self.assertEqual(cli.main(["logout", "--env-file", self.env_file]), 0)
        self.assertIsNone(DotEnvCredentialStore(self.env_file).load())

    def test_models_json_follows_the_filtered_catalog(self):
        from hackingBuddyGPT.cli import orcarouter as cli

        provider = OrcaRouterProvider(
            env={},
            catalog_client=FakeCatalogClient(
                [_model("acme/chat-1", input_modalities=frozenset({"text", "image"}))]
            ),
        )
        args = type("Args", (), {
            "capability": "chat", "modalities": "image", "json": True, "select": False,
            "model": "", "env_file": self.env_file, "api_base": "", "auth_base": "", "base_url": "",
        })()
        with patch("hackingBuddyGPT.cli.orcarouter._provider", return_value=provider):
            import io
            from contextlib import redirect_stdout

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = cli.cmd_models(args)
        self.assertEqual(code, 0)
        self.assertIn("acme/chat-1", buffer.getvalue())


class TestCatalogAgainstProvider(unittest.TestCase):
    def test_provider_applies_modality_filter(self):
        client = FakeCatalogClient([
            _model("acme/text-only"),
            _model("acme/vision", input_modalities=frozenset({"text", "image"})),
        ])
        provider = OrcaRouterProvider(env={}, catalog_client=client)
        self.assertEqual(provider.catalog("chat").ids, ["acme/text-only", "acme/vision"])
        self.assertEqual(provider.catalog("chat", ("image",)).ids, ["acme/vision"])


@unittest.skipUnless(os.environ.get("ORCAROUTER_API_KEY"), "ORCAROUTER_API_KEY is not set")
class TestLiveOrcaRouter(unittest.TestCase):
    """Real requests through the provider code path (no mocks)."""

    def setUp(self):
        self.store = DotEnvCredentialStore(Path(tempfile.mkdtemp()) / ".env")
        self.provider = OrcaRouterProvider(env=dict(os.environ), store=self.store)

    def test_live_catalog(self):
        result = self.provider.catalog("chat")
        self.assertEqual(result.source, "live")
        self.assertGreater(len(result.models), 0)
        self.assertEqual(self.provider.origins.api_base, "https://api.orcarouter.ai/v1")
        self.assertEqual(self.provider.origins.auth_base, "https://www.orcarouter.ai")
        self.assertTrue(all(model.endpoint_types & {"openai", "anthropic", "gemini", "openai-response"}
                            for model in result.models))

    def _candidate_models(self):
        offered = self.provider.catalog("chat").ids
        preferred = [LIVE_MODEL] if LIVE_MODEL in offered else []
        return preferred + [model for model in offered if model not in preferred]

    def test_live_chat_completion_through_the_provider(self):
        # Which models a key may use is workspace-specific, so the live check walks the catalog
        # the same way the CLI does instead of hard-coding one entitlement.
        candidates = self._candidate_models()
        self.assertTrue(candidates, "the live catalog offered no chat model")
        errors = []
        for model_id in candidates[:3]:
            llm = LiteLLM(
                api_key=os.environ["ORCAROUTER_API_KEY"],
                model=model_id,
                context_size=32000,
                preset="orcarouter",
                api_timeout=60,
            )
            try:
                llm.init()
                result = llm.get_response([{"role": "user", "content": "Reply with the word ok."}])
            except ModelSelectionError as exc:
                errors.append(f"{model_id}: {exc}")
                continue
            self.assertIsNotNone(result)
            self.assertGreater(result.tokens_query, 0)
            self.assertEqual(llm._preset_provider.origins.api_base, "https://api.orcarouter.ai/v1")
            return
        self.fail("no offered chat model accepted the request: " + "; ".join(errors))

    def test_cyber_model_is_documented_even_when_locked(self):
        llm = LiteLLM(
            api_key=os.environ["ORCAROUTER_API_KEY"],
            model=RECOMMENDED_CYBER_MODEL,
            context_size=32000,
            preset="orcarouter",
            api_timeout=60,
        )
        try:
            llm.init()
        except ModelSelectionError:
            # Not offered for this workspace: the catalog is authoritative, nothing is bypassed.
            self.assertNotIn(RECOMMENDED_CYBER_MODEL, self.provider.catalog("chat").ids)
            return
        try:
            llm.get_response([{"role": "user", "content": "Reply with the word ok."}])
        except ModelSelectionError as exc:
            self.assertIn("may not use the selected model", str(exc))


if __name__ == "__main__":
    unittest.main()
