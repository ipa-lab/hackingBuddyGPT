"""Model discovery, capability filtering and the catalog-backed selector."""

import json
import unittest

from hackingBuddyGPT.utils.orcarouter import catalog as catalog_module
from hackingBuddyGPT.utils.orcarouter.catalog import (
    VERIFIED_SEED,
    CatalogError,
    CatalogResult,
    ModelCatalog,
    ModelInfo,
    filter_models,
    parse_catalog,
)
from hackingBuddyGPT.utils.orcarouter.provider import ModelSelectionError, ModelSelector, OrcaRouterProvider

LIVE_PAYLOAD = {
    "object": "list",
    "data": [
        {
            "id": "deepseek/deepseek-v4.1-flash",
            "name": "DeepSeek V4.1 Flash",
            "context_window": 1048576,
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "supported_endpoint_types": ["openai", "openai-response", "anthropic"],
        },
        {
            "id": "deepseek/deepseek-v4-pro",
            "name": "DeepSeek V4 Pro",
            "context_window": 1048576,
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "supported_endpoint_types": ["openai", "openai-response"],
        },
        {
            "id": "orcarouter/fusion",
            "context_window": 1000000,
            "supported_endpoint_types": ["openai", "openai-response", "anthropic", "gemini"],
        },
        {
            "id": "acme/text-embed-3",
            "architecture": {"input_modalities": ["text"], "output_modalities": ["embedding"]},
            "supported_endpoint_types": ["embeddings"],
        },
        {
            "id": "acme/image-gen-2",
            "supported_endpoint_types": ["image-generation"],
        },
        {
            "id": "acme/video-gen-1",
            "supported_endpoint_types": ["openai-video"],
        },
        {
            "id": "acme/rerank-1",
            "supported_endpoint_types": ["jina-rerank"],
        },
        {"not_a_model": True},
        {"id": 17},
    ],
}


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, raw=None):
        self.status_code = status_code
        self._payload = payload
        self._raw = raw

    def iter_content(self, chunk_size=65536):
        raw = self._raw if self._raw is not None else json.dumps(self._payload).encode()
        for start in range(0, len(raw), chunk_size):
            yield raw[start : start + chunk_size]


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.gets = []

    def get(self, url, params=None, headers=None, timeout=None, stream=False):
        self.gets.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


class TestParsing(unittest.TestCase):
    def test_parses_declared_metadata_only(self):
        models = parse_catalog(LIVE_PAYLOAD)
        ids = [model.id for model in models]
        self.assertIn("deepseek/deepseek-v4.1-flash", ids)
        self.assertNotIn("not_a_model", ids)
        flash = next(model for model in models if model.id == "deepseek/deepseek-v4.1-flash")
        self.assertEqual(flash.context_window, 1048576)
        self.assertIn("image", flash.input_modalities)
        self.assertIn("openai", flash.endpoint_types)

    def test_missing_architecture_declares_no_modalities(self):
        models = parse_catalog(LIVE_PAYLOAD)
        fusion = next(model for model in models if model.id == "orcarouter/fusion")
        self.assertEqual(fusion.input_modalities, frozenset())

    def test_item_cap_and_invalid_payload(self):
        payload = {"data": [{"id": f"m/{index}"} for index in range(10)]}
        self.assertEqual(len(parse_catalog(payload, limit=3)), 3)
        with self.assertRaises(CatalogError):
            parse_catalog({"nope": []})
        with self.assertRaises(CatalogError):
            parse_catalog("a string")


class TestCapabilityFiltering(unittest.TestCase):
    def setUp(self):
        self.models = parse_catalog(LIVE_PAYLOAD)

    def ids(self, capability, modalities=()):
        return [model.id for model in filter_models(self.models, capability, modalities)]

    def test_chat_excludes_non_text_models(self):
        ids = self.ids("chat")
        self.assertIn("deepseek/deepseek-v4-pro", ids)
        self.assertIn("deepseek/deepseek-v4.1-flash", ids)
        self.assertIn("orcarouter/fusion", ids)
        self.assertNotIn("acme/image-gen-2", ids)
        self.assertNotIn("acme/video-gen-1", ids)
        self.assertNotIn("acme/rerank-1", ids)
        self.assertNotIn("acme/text-embed-3", ids)

    def test_multimodal_chat_requires_declared_image_input(self):
        ids = self.ids("chat", ("image",))
        self.assertEqual(ids, ["deepseek/deepseek-v4.1-flash"])  # fail closed for undeclared models

    def test_each_capability_matches_its_endpoint_type(self):
        self.assertEqual(self.ids("embedding"), ["acme/text-embed-3"])
        self.assertEqual(self.ids("image"), ["acme/image-gen-2"])
        self.assertEqual(self.ids("video"), ["acme/video-gen-1"])
        self.assertEqual(self.ids("rerank"), ["acme/rerank-1"])

    def test_unknown_capability_is_refused(self):
        with self.assertRaises(CatalogError):
            filter_models(self.models, "telepathy")


class TestDiscovery(unittest.TestCase):
    def test_live_catalog_is_authoritative(self):
        session = FakeSession(FakeResponse(LIVE_PAYLOAD))
        catalog = ModelCatalog("https://api.orcarouter.ai/v1", "sk-orca-test", session=session)
        result = catalog.fetch("chat")
        self.assertEqual(result.source, "live")
        self.assertFalse(result.degraded)
        self.assertNotIn("openai/gpt-5.5", result.ids)  # seed is never mixed into live results
        self.assertEqual(session.gets[0]["url"], "https://api.orcarouter.ai/v1/models")
        self.assertEqual(session.gets[0]["params"], {"capability": "chat"})
        self.assertEqual(session.gets[0]["headers"]["Authorization"], "Bearer sk-orca-test")

    def test_failure_falls_back_to_the_verified_seed(self):
        import requests

        for session in (
            FakeSession(error=requests.ConnectionError("down")),
            FakeSession(FakeResponse(status_code=500)),
            FakeSession(FakeResponse(raw=b"not json")),
        ):
            result = ModelCatalog("https://api.orcarouter.ai/v1", "k", session=session).fetch("chat")
            self.assertEqual(result.source, "seed")
            self.assertTrue(result.degraded)
            self.assertIn("orcarouter/auto", result.ids)

    def test_seed_preserves_reasoning_metadata(self):
        seed = {model.id: model for model in VERIFIED_SEED}
        self.assertEqual(seed["openai/gpt-5.5"].reasoning_efforts, ("low", "medium", "high", "xhigh"))
        self.assertTrue(all(model.endpoint_types for model in VERIFIED_SEED))

    def test_oversized_response_is_bounded(self):
        big = FakeResponse(raw=b"[" + b" " * (catalog_module.MAX_BYTES + 10) + b"]")
        result = ModelCatalog("https://api.orcarouter.ai/v1", "k", session=FakeSession(big)).fetch("chat")
        self.assertTrue(result.degraded)
        self.assertEqual(result.source, "seed")


class StaticCatalog:
    def __init__(self, models_by_capability):
        self.models_by_capability = models_by_capability
        self.calls = []

    def fetch(self, capability="chat"):
        self.calls.append(capability)
        models = self.models_by_capability.get(capability, [])
        return CatalogResult(models, source="live", capability=capability)


class TestModelSelector(unittest.TestCase):
    def setUp(self):
        self.chat_models = filter_models(parse_catalog(LIVE_PAYLOAD), "chat")
        self.image_models = filter_models(parse_catalog(LIVE_PAYLOAD), "chat", ("image",))
        self.client = StaticCatalog({"chat": self.chat_models, "embedding": []})
        self.provider = OrcaRouterProvider(env={}, catalog_client=self.client, out=lambda _: None)

    def test_options_come_from_the_catalog(self):
        selector = self.provider.selector("chat")
        selector.load()
        self.assertEqual(selector.options, [model.id for model in self.chat_models])

    def test_capability_change_recomputes_and_clears_stale_selection(self):
        selector = self.provider.selector("chat")
        selector.load()
        selector.select("deepseek/deepseek-v4-pro")
        self.assertEqual(selector.selected, "deepseek/deepseek-v4-pro")

        # Adding an image attachment re-filters the options; the text model is dropped.
        self.client.models_by_capability["chat"] = self.image_models
        selector.set_capability("chat", ("image",))
        self.assertEqual(selector.options, ["deepseek/deepseek-v4.1-flash"])
        self.assertIsNone(selector.selected)

    def test_incompatible_model_is_rejected_with_the_available_list(self):
        selector = self.provider.selector("chat")
        selector.load()
        with self.assertRaises(ModelSelectionError) as ctx:
            selector.select("acme/image-gen-2")
        self.assertIn("deepseek/deepseek-v4-pro", str(ctx.exception))

    def test_default_prefers_the_cyber_model_then_the_router_model(self):
        selector = ModelSelector(self.provider, out=lambda _: None)
        self.client.models_by_capability["chat"] = list(self.chat_models) + [
            ModelInfo(id="orcacyber-zero", endpoint_types=frozenset({"openai"}),
                      input_modalities=frozenset({"text"}))
        ]
        self.assertEqual(selector.default_model(), "orcacyber-zero")

        selector = ModelSelector(self.provider, out=lambda _: None)
        self.client.models_by_capability["chat"] = self.chat_models
        self.assertEqual(selector.default_model(), "orcarouter/fusion")

    def test_interactive_picker_uses_filtered_options(self):
        selector = self.provider.selector("chat", ("image",))
        self.client.models_by_capability["chat"] = self.image_models
        printed = []
        selector.out = printed.append
        chosen = selector.choose(input_fn=lambda _: "1")
        self.assertEqual(chosen, "deepseek/deepseek-v4.1-flash")
        self.assertTrue(any("deepseek/deepseek-v4.1-flash" in line for line in printed))
        self.assertFalse(any("acme/image-gen-2" in line for line in printed))

    def test_empty_catalog_is_an_error_not_free_text(self):
        provider = OrcaRouterProvider(env={}, catalog_client=StaticCatalog({}), out=lambda _: None)
        selector = provider.selector("embedding")
        selector.load()
        with self.assertRaises(ModelSelectionError):
            selector.choose(input_fn=lambda _: "text-embedding-3-large")


if __name__ == "__main__":
    unittest.main()
