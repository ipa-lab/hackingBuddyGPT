"""Registry of named LLM providers that are more than a bare model string.

The repository's default upstream is plain litellm (any provider through ``llm.model``).
A *preset* here is a provider this project ships first-class support for: its own base URL,
credential acquisition, model catalog and documentation.  Presets are selected with
``--llm.preset=<name>``; the OrcaRouter entry keeps its own name and configuration, it is
not a generic "any endpoint" passthrough.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .orcarouter import provider as orcarouter
from .orcarouter.provider import OrcaRouterProvider


@dataclass(frozen=True)
class ProviderPreset:
    """One named provider this project understands."""

    name: str
    label: str
    description: str
    api_base: str
    auth_base: str | None
    env_key: str
    docs_url: str
    keys_url: str
    default_model: str
    supports_pkce: bool
    factory: Callable[..., object]

    def create(self, **kwargs) -> object:
        return self.factory(**kwargs)


ORCAROUTER_PRESET = ProviderPreset(
    name=orcarouter.PRESET_NAME,
    label=orcarouter.LABEL,
    description=orcarouter.DESCRIPTION,
    api_base=orcarouter.BASE_URL,
    auth_base=orcarouter.AUTH_BASE_URL,
    env_key="ORCAROUTER_API_KEY",
    docs_url=orcarouter.DOCS_URL,
    keys_url=orcarouter.KEYS_URL,
    default_model=orcarouter.FALLBACK_DEFAULT_MODEL,
    supports_pkce=True,
    factory=OrcaRouterProvider,
)

PROVIDER_PRESETS: dict[str, ProviderPreset] = {ORCAROUTER_PRESET.name: ORCAROUTER_PRESET}


class UnknownProviderError(ValueError):
    """A preset name that this build does not ship."""


def get_preset(name: str) -> ProviderPreset:
    try:
        return PROVIDER_PRESETS[name]
    except KeyError:
        raise UnknownProviderError(
            f"unknown LLM provider preset {name!r} (available: {', '.join(sorted(PROVIDER_PRESETS))})"
        ) from None


def preset_names() -> list[str]:
    return sorted(PROVIDER_PRESETS)
