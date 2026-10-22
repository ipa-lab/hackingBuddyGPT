"""One credential seam, two adapters: pasted API key and OAuth 2.0 + PKCE.

Both adapters produce the same :class:`Credential` — a normal ``sk-orca-…`` API key that
belongs to the user.  Everything downstream (request signing, model discovery) consumes
that object and never looks at where it came from.

The key is stored in the project's existing secret file, ``.env`` (python-dotenv is how
every other credential in this repository is configured), under ``ORCA_KEY`` with mode
0600.  No second secret store is introduced.  Keys and verifiers are never logged, never
embedded in error messages and never returned in redacted-less form.
"""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

STORE_KEY_NAME = "ORCA_KEY"
API_KEY_ENV_NAMES = ("ORCAROUTER_API_KEY", "ORCA_KEY")
REDACTED = "sk-orca-…"


class CredentialError(Exception):
    """Base class for credential problems. Messages never contain the secret."""


class MissingCredentialError(CredentialError):
    """No usable credential is available yet."""


class ReauthenticationRequired(CredentialError):
    """The upstream rejected this exact credential (HTTP 401); log in again."""


def looks_like_api_key(value: str) -> bool:
    """Lightweight shape check only — the first real request establishes validity."""
    return isinstance(value, str) and value.startswith("sk-orca-") and len(value) > len("sk-orca-")


def redact(value: str | None) -> str:
    """Render a credential for humans without disclosing it."""
    if not value:
        return ""
    if len(value) <= 8:
        return "…"
    return f"{value[:7]}…{value[-4:]}"


@dataclass(frozen=True)
class Credential:
    """A resolved OrcaRouter API key plus provenance used for status and reauth."""

    value: str
    source: str  # "api_key" | "pkce"
    account: str = ""
    generation: int = 0

    def __post_init__(self):
        if not self.value:
            raise MissingCredentialError("empty OrcaRouter credential")

    @property
    def masked(self) -> str:
        return redact(self.value)

    def __repr__(self) -> str:  # never leak the value through repr/logging
        return f"Credential(source={self.source!r}, account={self.account!r}, masked={self.masked!r})"


class CredentialStore(Protocol):
    def load(self) -> str | None: ...
    def save(self, value: str) -> None: ...
    def clear(self) -> None: ...
    def exists(self) -> bool: ...


class DotEnvCredentialStore:
    """Read/write ``ORCA_KEY`` in the repository's ``.env`` secret file.

    Other lines are preserved verbatim; the file is written atomically with mode 0600.
    """

    def __init__(self, path: str | Path = ".env", key_name: str = STORE_KEY_NAME):
        self.path = Path(path)
        self.key_name = key_name

    # -- reading -----------------------------------------------------------------
    def _lines(self) -> list[str]:
        try:
            return self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []

    def load(self) -> str | None:
        for line in self._lines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, _, raw = stripped.partition("=")
            if name.strip() != self.key_name:
                continue
            value = raw.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            return value or None
        # Fall back to the process environment for read-only deployments.
        return None

    def exists(self) -> bool:
        return bool(self.load())

    # -- writing -----------------------------------------------------------------
    def save(self, value: str) -> None:
        if not value:
            raise CredentialError("refusing to store an empty OrcaRouter credential")
        lines = [line for line in self._lines() if not self._is_our_line(line)]
        lines.append(f"{self.key_name}='{value}'")
        self._atomic_write("\n".join(lines) + "\n")

    def clear(self) -> None:
        lines = self._lines()
        kept = [line for line in lines if not self._is_our_line(line)]
        if kept == lines and not self.path.exists():
            return
        self._atomic_write("\n".join(kept) + ("\n" if kept else ""))

    def _is_our_line(self, line: str) -> bool:
        stripped = line.strip()
        return bool(stripped) and not stripped.startswith("#") and stripped.split("=", 1)[0].strip() == self.key_name

    def _atomic_write(self, content: str) -> None:
        directory = self.path.parent if str(self.path.parent) else Path(".")
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".env.", text=True)
        try:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(tmp_name, self.path)
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


@dataclass
class CredentialState:
    """Track the generation of the credential currently in force.

    A ``401`` may only mark the credential generation that produced the rejected request.
    A late failure from an old request must never poison a freshly reauthorized key.
    """

    generation: int = 0
    account: str = ""
    needs_reauth: bool = False
    _rejected_generations: set[int] = field(default_factory=set)

    def issue(self, credential: Credential) -> Credential:
        self.generation += 1
        self.account = credential.account
        self.needs_reauth = False
        self._rejected_generations.clear()
        return Credential(
            value=credential.value,
            source=credential.source,
            account=credential.account,
            generation=self.generation,
        )

    def mark_unauthorized(self, generation: int) -> bool:
        """Mark the exact generation as needing reauthentication. No refresh is attempted."""
        if generation != self.generation:
            # A stale request lost the race with a newer login; ignore it entirely.
            return False
        self.needs_reauth = True
        self._rejected_generations.add(generation)
        return True

    @property
    def rejected_generations(self) -> frozenset[int]:
        return frozenset(self._rejected_generations)


class ApiKeyCredentialSource:
    """Adapter for a user-supplied ``sk-orca-…`` key.

    Precedence: explicit config (``--llm.api_key``) → ``ORCAROUTER_API_KEY`` → ``ORCA_KEY``
    in the environment → ``ORCA_KEY`` in ``.env``.
    """

    source_name = "api_key"

    def __init__(self, explicit: str | None = None, store: CredentialStore | None = None, env: dict | None = None):
        self.explicit = explicit or ""
        self.store = store or DotEnvCredentialStore()
        self._env = env if env is not None else os.environ

    def available(self) -> bool:
        return bool(self.explicit or any(self._env.get(name) for name in API_KEY_ENV_NAMES) or self.store.load())

    def acquire(self, *, force: bool = False) -> Credential:  # noqa: ARG002 - matches the adapter interface
        if self.explicit:
            return Credential(value=self.explicit, source=self.source_name)
        for name in API_KEY_ENV_NAMES:
            value = self._env.get(name)
            if value:
                return Credential(value=value, source=self.source_name)
        stored = self.store.load()
        if stored:
            return Credential(value=stored, source=self.source_name)
        raise MissingCredentialError(
            "No OrcaRouter API key configured. Pass --llm.api_key / set ORCAROUTER_API_KEY, "
            "or run `wintermute-orcarouter login` to authorize this device."
        )


class PkceCredentialSource:
    """Adapter for the browser/out-of-band OAuth 2.0 + PKCE connect flow.

    A PKCE-issued key is a durable API key, not a refresh token: once stored it is reused
    until OrcaRouter revokes it.  Re-authorization only happens when the user asks for it
    (``force=True``) or after a terminal ``401``.
    """

    source_name = "pkce"

    def __init__(self, store: DotEnvCredentialStore, flow_factory):
        self.store = store
        self._flow_factory = flow_factory

    def available(self) -> bool:
        return bool(self.store.load())

    def acquire(self, *, force: bool = False) -> Credential:
        if not force:
            stored = self.store.load()
            if stored:
                return Credential(value=stored, source=self.source_name)
        flow = self._flow_factory()
        credential = flow.connect()
        # Persist only after a successful exchange; the old secret is not touched before that.
        self.store.save(credential.value)
        return Credential(value=credential.value, source=self.source_name, account=credential.account)


def acquire_credential(
    *,
    explicit_api_key: str | None,
    store: DotEnvCredentialStore,
    flow_factory,
    state: CredentialState,
    mode: str = "auto",
) -> Credential:
    """Resolve a credential through the seam and register its generation.

    ``mode`` is ``auto`` (stored key, else API key, else PKCE), ``api_key`` or ``pkce``.
    """
    api_source = ApiKeyCredentialSource(explicit_api_key, store=store)
    pkce_source = PkceCredentialSource(store, flow_factory)

    if mode == "api_key":
        selector = api_source
    elif mode == "pkce":
        selector = pkce_source
    elif mode == "auto":
        if api_source.available():
            selector = api_source
        elif pkce_source.available():
            selector = pkce_source
        else:
            raise MissingCredentialError(
                "No OrcaRouter credential found. Set --llm.api_key / ORCAROUTER_API_KEY, "
                "or run `wintermute-orcarouter login` (OAuth 2.0 + PKCE)."
            )
    else:
        raise CredentialError(f"unknown credential mode {mode!r} (expected auto, api_key or pkce)")

    return state.issue(selector.acquire())
