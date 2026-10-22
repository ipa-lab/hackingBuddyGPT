"""The named OrcaRouter provider.

This is the single place that knows OrcaRouter's identity, origins, credential sources,
model catalog and request shape.  ``LiteLLM`` delegates to it when the user selects
``--llm.preset=orcarouter``; the benchmark launcher and the CLI use the same object, so the
provider list, the config and the docs can never drift apart.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable

from .catalog import CatalogError, CatalogResult, ModelCatalog, ModelInfo
from .config import Origins
from .credentials import (
    Credential,
    CredentialState,
    DotEnvCredentialStore,
    MissingCredentialError,
    ReauthenticationRequired,
    acquire_credential,
)
from .pkce import PkceFlow

PRESET_NAME = "orcarouter"
LABEL = "OrcaRouter"
DESCRIPTION = "OrcaRouter — OpenAI-compatible gateway (API key or OAuth 2.0 + PKCE)"
BASE_URL = "https://api.orcarouter.ai/v1"
AUTH_BASE_URL = "https://www.orcarouter.ai"
DOCS_URL = "https://www.orcarouter.ai/docs"
KEYS_URL = "https://www.orcarouter.ai/console/token"
AUTHORIZED_APPS_URL = "https://www.orcarouter.ai/console/authorized-apps"

# Recommended for authorized security work; unlocked per workspace after business
# verification, so the ordinary default falls back to the general-purpose router model.
RECOMMENDED_CYBER_MODEL = "orcacyber-zero"
FALLBACK_DEFAULT_MODEL = "orcarouter/fusion"


class ModelSelectionError(Exception):
    """The requested model is not offered by OrcaRouter for this entry point."""


@dataclass
class ModelSelector:
    """Catalog-backed model choices for one capability of one entry point.

    Changing the capability (or the required modalities) recomputes the options; a
    selection that is no longer compatible is dropped instead of being silently kept.
    """

    provider: "OrcaRouterProvider"
    capability: str = "chat"
    modalities: tuple[str, ...] = ()
    out: Callable[[str], None] = print

    _catalog: CatalogResult | None = field(default=None, init=False, repr=False)
    _selected: str | None = field(default=None, init=False)

    def load(self) -> CatalogResult:
        self._catalog = self.provider.catalog(self.capability, self.modalities)
        if self._catalog.degraded:
            self.out(
                f"[OrcaRouter] live model discovery unavailable ({self._catalog.detail}); "
                f"using the verified fallback catalog ({len(self._catalog.models)} models)."
            )
        if self._selected and self._selected not in self._catalog.ids:
            self.out(
                f"[OrcaRouter] previously selected model {self._selected!r} is not compatible with "
                f"capability {self.capability!r}; choose another model."
            )
            self._selected = None
        return self._catalog

    def set_capability(self, capability: str, modalities: tuple[str, ...] = ()) -> CatalogResult:
        self.capability = capability
        self.modalities = tuple(modalities)
        return self.load()

    @property
    def options(self) -> list[str]:
        return list(self._catalog.ids) if self._catalog else []

    @property
    def selected(self) -> str | None:
        return self._selected

    def select(self, model_id: str) -> str:
        if self._catalog is None:
            self.load()
        if model_id not in self._catalog.ids:
            raise ModelSelectionError(
                f"{model_id!r} is not offered by OrcaRouter for {self.capability!r} with this credential. "
                f"Available: {', '.join(self._catalog.ids[:20]) or '(none)'}"
            )
        self._selected = model_id
        return model_id

    def default_model(self) -> str | None:
        if self._catalog is None:
            self.load()
        options = self._catalog.ids
        for candidate in (RECOMMENDED_CYBER_MODEL, FALLBACK_DEFAULT_MODEL):
            if candidate in options:
                return candidate
        return options[0] if options else None

    def choose(self, prompt: str = "Select an OrcaRouter model", input_fn: Callable[[str], str] = input) -> str:
        """Interactive picker over the live catalog — the CLI's equivalent of a dropdown."""
        if self._catalog is None:
            self.load()
        options = self._catalog.ids
        if not options:
            raise ModelSelectionError(
                f"OrcaRouter offers no models for capability {self.capability!r} with this credential."
            )
        if len(options) == 1:
            self.out(f"{prompt}: {options[0]} (only compatible model)")
            return self.select(options[0])

        self.out("")
        self.out(f"{prompt} ({len(options)} models):")
        for index, model_id in enumerate(options, start=1):
            self.out(f"  {index:>3}. {model_id}")
        while True:
            raw = input_fn(f"Model [1-{len(options)}, id accepted]: ").strip()
            if not raw:
                continue
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return self.select(options[int(raw) - 1])
            if raw in options:
                return self.select(raw)
            self.out(f"{raw!r} is not in the list. Enter a number, or one of the model ids above.")


@dataclass
class OrcaRouterProvider:
    """Named supplier of credentials, models and request parameters for OrcaRouter."""

    name: str = PRESET_NAME
    label: str = LABEL
    description: str = DESCRIPTION

    api_base: str | None = None
    auth_base: str | None = None
    shared_base: str | None = None
    env: dict | None = None
    credential_mode: str = "auto"
    dotenv_path: str = ".env"
    interactive: bool | None = None
    out: Callable[[str], None] = print
    flow_factory: Callable[..., object] | None = None
    store: DotEnvCredentialStore | None = None
    catalog_client: ModelCatalog | None = None
    session: object | None = None

    _origins: Origins | None = field(default=None, init=False, repr=False)
    _credential: Credential | None = field(default=None, init=False, repr=False)
    _state: CredentialState = field(default_factory=CredentialState, init=False, repr=False)
    _store: DotEnvCredentialStore | None = field(default=None, init=False, repr=False)

    # -- identity -------------------------------------------------------------------
    def __post_init__(self):
        self._store = self.store or DotEnvCredentialStore(self.dotenv_path)
        self._origins = Origins.resolve(
            auth_base=self.auth_base, api_base=self.api_base, shared=self.shared_base, env=self.env
        )

    @property
    def origins(self) -> Origins:
        return self._origins

    @property
    def models_url(self) -> str:
        return self._origins.models_url("chat")

    @property
    def keys_url(self) -> str:
        return KEYS_URL

    def docs_table_row(self) -> str:
        return f"| {self.label} | `{BASE_URL}` | `--llm.preset={self.name}` |"

    # -- credentials ------------------------------------------------------------------
    def _make_flow(self):
        if self.flow_factory is not None:
            return self.flow_factory()
        return PkceFlow(origins=self._origins, session=self.session or __import__("requests").Session())

    def credential(self, *, force_login: bool = False) -> Credential:
        """Resolve through the seam (API key or PKCE) and register the generation."""
        if self._credential is not None and not force_login:
            return self._credential
        credential = acquire_credential(
            explicit_api_key=None,
            store=self._store,
            flow_factory=self._make_flow,
            state=self._state,
            mode=self.credential_mode,
        )
        self._credential = credential
        return credential

    def set_api_key(self, value: str) -> Credential:
        """Register an explicitly configured key (the ``--llm.api_key`` adapter)."""
        from .credentials import Credential as _Credential

        self._credential = self._state.issue(_Credential(value=value, source="api_key"))
        return self._credential

    def mark_unauthorized(self, generation: int | None = None) -> bool:
        generation = self._state.generation if generation is None else generation
        return self._state.mark_unauthorized(generation)

    @property
    def credential_state(self) -> CredentialState:
        return self._state

    # -- catalog ----------------------------------------------------------------------
    def catalog(self, capability: str = "chat", modalities: tuple[str, ...] = ()) -> CatalogResult:
        from .catalog import filter_models

        if self.catalog_client is not None:
            result = self.catalog_client.fetch(capability)
        else:
            credential = self.credential()
            client_kwargs = {"session": self.session} if self.session is not None else {}
            result = ModelCatalog(self._origins.api_base, credential.value, **client_kwargs).fetch(capability)
        if modalities and capability == "chat":
            return CatalogResult(
                filter_models(result.models, capability, modalities),
                source=result.source,
                degraded=result.degraded,
                detail=result.detail,
                capability=capability,
            )
        return result

    def selector(self, capability: str = "chat", modalities: tuple[str, ...] = ()) -> ModelSelector:
        return ModelSelector(self, capability=capability, modalities=modalities, out=self.out)

    def resolve_chat_model(self, requested: str = "", *, allow_interactive: bool | None = None) -> str:
        """Validate (or pick) a chat model from the live catalog."""
        selector = self.selector("chat")
        selector.load()
        if requested:
            return selector.select(requested)
        interactive = self.interactive if allow_interactive is None else allow_interactive
        if interactive is None:
            interactive = sys.stdin.isatty()
        if interactive:
            return selector.choose()
        default = selector.default_model()
        raise ModelSelectionError(
            "No --llm.model selected for OrcaRouter. "
            f"Recommended default: {default or '(no model available)'}. "
            f"Run `wintermute-orcarouter models --select` to choose from the catalog "
            f"({', '.join(selector.options[:20]) or 'no models returned'})."
        )

    def embedding_model(self, requested: str = "") -> str:
        selector = self.selector("embedding")
        result = selector.load()
        if requested:
            return selector.select(requested)
        if result.ids:
            return result.ids[0]
        raise ModelSelectionError(
            "OrcaRouter offers no embedding-capable model for this credential; "
            "set an embedding model explicitly or disable --rag_path."
        )

    # -- request shape ------------------------------------------------------------------
    def completion_kwargs(self, model: str, credential: Credential | None = None) -> dict:
        """litellm keyword arguments for the OpenAI-compatible relay."""
        credential = credential or self.credential()
        return {
            "model": f"openai/{model}",
            "api_base": self._origins.api_base,
            "api_key": credential.value,
        }

    def chat_model_label(self, model: str) -> str:
        return f"{self.label}: {model}"

    def check_response_error(self, error: BaseException) -> None:
        """Classify upstream errors; a 401 is terminal reauthentication, never a retry."""
        status = getattr(error, "status_code", None)
        if status is None:
            response = getattr(error, "response", None)
            status = getattr(response, "status_code", None)
        if status == 401:
            self.mark_unauthorized()
            raise ReauthenticationRequired(
                "OrcaRouter rejected this credential (HTTP 401). It has been revoked or expired; "
                "run `wintermute-orcarouter login` or update --llm.api_key. "
                "No automatic refresh was attempted."
            ) from error
        if status == 403:
            message = str(error).lower()
            if "model_access_denied" in message:
                raise ModelSelectionError(
                    "This OrcaRouter credential may not use the selected model. Choose another model with "
                    "`wintermute-orcarouter models --select`, or grant the key access in the console at "
                    f"{self.keys_url}."
                ) from error


def default_selector(provider: OrcaRouterProvider, capability: str = "chat") -> ModelSelector:
    return provider.selector(capability)


def model_names(models: list[ModelInfo]) -> list[str]:
    return [model.id for model in models]


__all__ = [
    "AUTHORIZED_APPS_URL",
    "BASE_URL",
    "DOCS_URL",
    "FALLBACK_DEFAULT_MODEL",
    "KEYS_URL",
    "LABEL",
    "ModelSelectionError",
    "ModelSelector",
    "OrcaRouterProvider",
    "PRESET_NAME",
    "RECOMMENDED_CYBER_MODEL",
    "CatalogError",
    "MissingCredentialError",
]
