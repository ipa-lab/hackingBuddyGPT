"""Origins and URL policy for OrcaRouter.

Authentication and inference live on **different public origins**.  Keeping them in one
place (instead of deriving one from the other by rewriting a hostname or appending ``/v1``)
is what stops an integration from sending a code exchange to the relay host, where
``/v1/auth/keys`` is a 404.

Overrides, highest priority first:

* explicit constructor/CLI values,
* ``ORCA_AUTH_BASE_URL`` / ``ORCA_API_BASE_URL`` for one origin each,
* ``ORCA_BASE_URL`` as a shared self-hosted base used for both,
* the public defaults below.

Remote origins must be HTTPS.  Plain HTTP is only accepted for loopback development.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_AUTH_BASE = "https://www.orcarouter.ai"
DEFAULT_API_BASE = "https://api.orcarouter.ai/v1"

AUTHORIZE_PATH = "/auth"
EXCHANGE_PATH = "/api/v1/auth/keys"
MODELS_PATH = "/models"

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]", "::1"})


class OriginError(ValueError):
    """An origin was not an acceptable URL (scheme, userinfo, fragment, ...)."""


def validate_origin(url: str, *, name: str = "origin") -> str:
    """Return ``url`` without a trailing slash after checking the transport policy."""
    if not isinstance(url, str) or not url.strip():
        raise OriginError(f"{name} must be a non-empty URL")
    candidate = url.strip()
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https"):
        raise OriginError(f"{name} must use http or https, got {parts.scheme or '<none>'!r}")
    if not parts.hostname:
        raise OriginError(f"{name} has no host")
    if parts.username or parts.password:
        raise OriginError(f"{name} must not contain userinfo")
    if parts.fragment:
        raise OriginError(f"{name} must not contain a fragment")
    if parts.scheme == "http" and parts.hostname.lower() not in LOOPBACK_HOSTS:
        raise OriginError(f"{name} must use https unless it points at loopback")
    return candidate.rstrip("/")


def _env(env: dict[str, str] | None) -> dict[str, str]:
    if env is not None:
        return env
    import os

    return dict(os.environ)


def resolve_auth_base(
    explicit: str | None = None,
    shared: str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> str:
    """Resolve the authentication origin (``https://www.orcarouter.ai`` by default)."""
    environment = _env(env)
    for value, name in (
        (explicit, "auth base URL"),
        (environment.get("ORCA_AUTH_BASE_URL"), "ORCA_AUTH_BASE_URL"),
        (shared, "shared base URL"),
        (environment.get("ORCA_BASE_URL"), "ORCA_BASE_URL"),
    ):
        if value:
            return validate_origin(value, name=name)
    return DEFAULT_AUTH_BASE


def resolve_api_base(
    explicit: str | None = None,
    shared: str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> str:
    """Resolve the inference origin, always including the ``/v1`` relay prefix."""
    environment = _env(env)
    for value, name in (
        (explicit, "API base URL"),
        (environment.get("ORCA_API_BASE_URL"), "ORCA_API_BASE_URL"),
    ):
        if value:
            return validate_origin(value, name=name)

    for value, name in (
        (shared, "shared base URL"),
        (environment.get("ORCA_BASE_URL"), "ORCA_BASE_URL"),
    ):
        if value:
            base = validate_origin(value, name=name)
            # A shared self-hosted base names one deployment for both surfaces; the relay
            # prefix is added once, never derived from the auth host.
            return base if base.endswith("/v1") else base + "/v1"
    return DEFAULT_API_BASE


@dataclass(frozen=True)
class Origins:
    """The two public origins, resolved once and never derived from each other."""

    auth_base: str
    api_base: str

    @classmethod
    def resolve(
        cls,
        *,
        auth_base: str | None = None,
        api_base: str | None = None,
        shared: str | None = None,
        env: dict[str, str] | None = None,
    ) -> "Origins":
        return cls(
            auth_base=resolve_auth_base(auth_base, shared, env=env),
            api_base=resolve_api_base(api_base, shared, env=env),
        )

    def authorize_url(self) -> str:
        return self.auth_base + AUTHORIZE_PATH

    def exchange_url(self) -> str:
        return self.auth_base + EXCHANGE_PATH

    def models_url(self, capability: str | None = None) -> str:
        url = self.api_base + MODELS_PATH
        if capability:
            url += f"?capability={capability}"
        return url
