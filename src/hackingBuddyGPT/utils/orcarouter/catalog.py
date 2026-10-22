"""Model discovery and capability filtering for OrcaRouter.

The only source of truth is ``GET {api_base}/models`` on the configured origin.  Nothing
here guesses capabilities from a model name: a model declares the endpoint types and input
modalities it supports, and anything undeclared is excluded (fail closed).

Responses are bounded (timeout, byte cap, item cap, accepted shape) so a catalog can never
consume unbounded memory or advertise routes this client cannot speak.  When discovery
fails, a small **verified seed** keeps a fresh installation usable; it is never mixed into
a successful live result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import requests

MAX_ITEMS = 2000
MAX_BYTES = 4 * 1024 * 1024
MAX_ID_LENGTH = 200
REQUEST_TIMEOUT = 10.0

CHAT_ENDPOINT_TYPES = frozenset({"openai", "anthropic", "gemini", "openai-response"})
NON_CHAT_ENDPOINT_TYPES = frozenset({"image-generation", "openai-video", "jina-rerank", "embeddings"})
EMBEDDING_ENDPOINT_TYPES = frozenset({"embeddings"})
IMAGE_ENDPOINT_TYPES = frozenset({"image-generation"})
VIDEO_ENDPOINT_TYPES = frozenset({"openai-video"})
RERANK_ENDPOINT_TYPES = frozenset({"jina-rerank"})

CAPABILITIES = ("chat", "embedding", "image", "video", "rerank")
MODALITIES = ("image", "audio", "video", "text")


class CatalogError(Exception):
    """The catalog could not be fetched or parsed."""


@dataclass(frozen=True)
class ModelInfo:
    """One model, with only the metadata the catalog actually declared."""

    id: str
    name: str = ""
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_modalities: frozenset[str] = frozenset()
    output_modalities: frozenset[str] = frozenset()
    endpoint_types: frozenset[str] = frozenset()
    reasoning_efforts: tuple[str, ...] = ()
    source: str = "live"

    @property
    def supports_chat(self) -> bool:
        if not self.endpoint_types & CHAT_ENDPOINT_TYPES:
            return False
        return not self.endpoint_types <= NON_CHAT_ENDPOINT_TYPES


@dataclass
class CatalogResult:
    """A filtered catalog plus how it was obtained."""

    models: list[ModelInfo]
    source: str  # "live" | "seed"
    degraded: bool = False
    detail: str = ""
    capability: str = "chat"

    @property
    def ids(self) -> list[str]:
        return [model.id for model in self.models]


def _as_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _string_set(value) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set)):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str) and item)


def parse_model(item) -> ModelInfo | None:
    """Accept only the shape we understand; everything else is dropped."""
    if not isinstance(item, dict):
        return None
    model_id = item.get("id")
    if not isinstance(model_id, str) or not model_id or len(model_id) > MAX_ID_LENGTH:
        return None
    if any(char.isspace() for char in model_id):
        return None
    architecture = item.get("architecture") if isinstance(item.get("architecture"), dict) else {}
    efforts = item.get("reasoning_efforts") or item.get("reasoning_effort") or ()
    if isinstance(efforts, str):
        efforts = (efforts,)
    return ModelInfo(
        id=model_id,
        name=item.get("name") if isinstance(item.get("name"), str) else "",
        context_window=_as_int(item.get("context_window")) or _as_int(item.get("context_length")),
        max_output_tokens=_as_int(item.get("max_output_tokens")),
        input_modalities=_string_set(architecture.get("input_modalities")),
        output_modalities=_string_set(architecture.get("output_modalities")),
        endpoint_types=_string_set(item.get("supported_endpoint_types")),
        reasoning_efforts=tuple(effort for effort in efforts if isinstance(effort, str)),
    )


def parse_catalog(payload, *, limit: int = MAX_ITEMS) -> list[ModelInfo]:
    if isinstance(payload, dict):
        items = payload.get("data")
    else:
        items = payload
    if not isinstance(items, list):
        raise CatalogError("catalog response has no model list")
    models: list[ModelInfo] = []
    seen: set[str] = set()
    for item in items[:limit]:
        model = parse_model(item)
        if model is None or model.id in seen:
            continue
        seen.add(model.id)
        models.append(model)
    return models


def filter_models(
    models: Iterable[ModelInfo],
    capability: str = "chat",
    modalities: Sequence[str] = (),
) -> list[ModelInfo]:
    """Filter by capability, then by required input modalities (fail closed)."""
    if capability not in CAPABILITIES:
        raise CatalogError(f"unknown capability {capability!r} (expected one of {', '.join(CAPABILITIES)})")
    required = frozenset(m for m in modalities if m and m != "text")
    result = []
    for model in models:
        if capability == "chat":
            if not model.supports_chat:
                continue
            if required and not required <= model.input_modalities:
                continue
        elif capability == "embedding":
            if not (model.endpoint_types & EMBEDDING_ENDPOINT_TYPES):
                continue
        elif capability == "image":
            if not (model.endpoint_types & IMAGE_ENDPOINT_TYPES):
                continue
        elif capability == "video":
            if not (model.endpoint_types & VIDEO_ENDPOINT_TYPES):
                continue
        elif capability == "rerank":
            if not (model.endpoint_types & RERANK_ENDPOINT_TYPES):
                continue
        result.append(model)
    return sorted(result, key=lambda model: model.id)


# Verified outage fallback.  These are the general OrcaRouter seed models; metadata is kept
# deliberately conservative (text input unless the catalog says otherwise) because the live
# catalog is authoritative.  GPT-5.5 keeps its published reasoning-effort ladder.
# Source: https://api.orcarouter.ai/v1/models (verified 2026-10-22) + campaign seed list.
VERIFIED_SEED: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="openai/gpt-5.5",
        name="OpenAI: GPT-5.5",
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"openai", "openai-response"}),
        reasoning_efforts=("low", "medium", "high", "xhigh"),
        source="seed",
    ),
    ModelInfo(
        id="anthropic/claude-opus-4.8",
        name="Anthropic: Claude Opus 4.8",
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"anthropic", "openai"}),
        source="seed",
    ),
    ModelInfo(
        id="google/gemini-3.5-flash",
        name="Google: Gemini 3.5 Flash",
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"gemini", "openai"}),
        source="seed",
    ),
    ModelInfo(
        id="deepseek/deepseek-v4-pro",
        name="DeepSeek: DeepSeek V4 Pro",
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"openai", "openai-response"}),
        source="seed",
    ),
    ModelInfo(
        id="orcarouter/auto",
        name="OrcaRouter: Auto",
        input_modalities=frozenset({"text"}),
        output_modalities=frozenset({"text"}),
        endpoint_types=frozenset({"openai", "openai-response"}),
        source="seed",
    ),
)


@dataclass
class ModelCatalog:
    """Fetch, bound and cache the catalog for one credential."""

    api_base: str
    api_key: str
    timeout: float = REQUEST_TIMEOUT
    session: object = field(default_factory=requests.Session)

    def fetch(self, capability: str = "chat") -> CatalogResult:
        if capability not in CAPABILITIES:
            raise CatalogError(f"unknown capability {capability!r}")
        url = self.api_base.rstrip("/") + "/models"
        try:
            response = self.session.get(
                url,
                params={"capability": capability},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            return self._fallback(capability, f"catalog request failed ({type(exc).__name__})")

        status = getattr(response, "status_code", 0)
        if status != 200:
            return self._fallback(capability, f"catalog answered HTTP {status}")
        try:
            body = self._bounded_body(response)
        except CatalogError as exc:
            return self._fallback(capability, str(exc))
        try:
            models = parse_catalog(body)
        except (CatalogError, ValueError):
            return self._fallback(capability, "catalog response was not valid JSON")

        filtered = filter_models(models, capability)
        if not filtered:
            return CatalogResult([], source="live", capability=capability)
        return CatalogResult(filtered, source="live", capability=capability)

    def _bounded_body(self, response) -> object:
        import json

        raw = b""
        iterator = getattr(response, "iter_content", None)
        if iterator is not None:
            for chunk in iterator(chunk_size=65536):
                raw += chunk
                if len(raw) > MAX_BYTES:
                    raise CatalogError("catalog response exceeded the size limit")
        else:  # test doubles
            content = getattr(response, "content", b"") or b""
            raw = content[:MAX_BYTES]
        try:
            return json.loads(raw)
        except ValueError:
            raise CatalogError("catalog response was not valid JSON") from None

    def _fallback(self, capability: str, detail: str) -> CatalogResult:
        models = filter_models(VERIFIED_SEED, capability)
        return CatalogResult(models, source="seed", degraded=True, detail=detail, capability=capability)
