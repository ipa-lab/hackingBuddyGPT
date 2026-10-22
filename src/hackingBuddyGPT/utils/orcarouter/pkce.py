"""OAuth 2.0 + PKCE login for OrcaRouter (Flow A loopback and Flow B out-of-band).

Both flows follow the same shape: a fresh cryptographically random *verifier* per
attempt, only its SHA-256 *challenge* (base64url, no padding) on the authorize URL, and a
constant-time ``state`` comparison before the returned code is used.  The verifier never
leaves this process and is never logged; the exchange happens on the **auth origin**
(``https://www.orcarouter.ai/api/v1/auth/keys``), never on the inference origin.

A successful exchange returns an ordinary ``sk-orca-…`` API key.  It is durable, not a
refresh token: there is no refresh grant to call and no proactive rotation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlsplit

import requests

from .config import Origins
from .credentials import Credential, CredentialError

APP_NAME = "hackingBuddyGPT"
DEFAULT_SCOPE = "api"
CALLBACK_PATH = "/cb"
LOOPBACK_HOST = "127.0.0.1"
CODE_TTL_SECONDS = 600


class PkceError(CredentialError):
    """Base class for authorization failures. Messages never include codes or verifiers."""


class AuthorizationDenied(PkceError):
    """The user declined the consent screen."""


class StateMismatch(PkceError):
    """The callback did not echo the state this process generated."""


class AuthorizationTimeout(PkceError):
    """No callback arrived before the local deadline."""


class ExchangeRejected(PkceError):
    """The code was unknown, expired or already used (HTTP 403)."""


class ChallengeRejected(PkceError):
    """The exchange was refused because of the challenge method (HTTP 400)."""


class RateLimited(PkceError):
    """Too many code issuances for this account (HTTP 429)."""


class ScopeDowngrade(PkceError):
    """The granted scope does not cover what this client needs."""


class AuthNetworkError(PkceError):
    """The auth origin could not be reached or answered something unusable."""


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def create_pkce_pair() -> tuple[str, str]:
    """Return ``(verifier, challenge)`` from a fresh cryptographic RNG."""
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def create_state() -> str:
    return b64url(secrets.token_bytes(16))


def build_authorize_url(
    origins: Origins,
    *,
    callback_url: str,
    challenge: str,
    state: str,
    app_name: str = APP_NAME,
    scope: str = DEFAULT_SCOPE,
    login_hint: str | None = None,
    workspace_hint: str | None = None,
) -> str:
    """Build the consent URL. The verifier is deliberately absent."""
    params = {
        "callback_url": callback_url,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "app_name": app_name,
        "scope": scope,
    }
    if login_hint:
        params["login_hint"] = login_hint
    if workspace_hint:
        params["workspace_hint"] = workspace_hint
    return f"{origins.authorize_url()}?{urlencode(params)}"


@dataclass
class PkceFlow:
    """Run one authorization attempt and exchange its code for an API key."""

    origins: Origins
    app_name: str = APP_NAME
    scope: str = DEFAULT_SCOPE
    timeout: float = 300.0
    session: object = field(default_factory=requests.Session)
    opener: Callable[[str], bool] | None = None
    prompt: Callable[[str], str] = input
    out: Callable[[str], None] = print

    # -- public -------------------------------------------------------------------
    def connect(self, *, mode: str = "auto") -> Credential:
        """Authorize and return the resulting credential.

        ``mode`` is ``loopback`` (Flow A), ``oob`` (Flow B) or ``auto`` (Flow A when a
        local browser/listener is reasonable, else Flow B).
        """
        verifier, challenge = create_pkce_pair()
        state = create_state()

        if mode == "auto":
            mode = "loopback"
        if mode == "loopback":
            code = self._loopback_code(challenge, state)
        elif mode == "oob":
            code = self._oob_code(challenge, state)
        else:
            raise PkceError(f"unknown authorization mode {mode!r}")

        payload = self.exchange(code, verifier)
        granted = payload.get("scope") or ""
        if granted != self.scope:
            # Report what was actually granted instead of assuming the requested scope.
            raise ScopeDowngrade(
                f"OrcaRouter granted scope {granted!r}, but this client needs {self.scope!r}. "
                "Nothing was stored; ask a workspace admin for an API-scope authorization."
            )
        return Credential(value=payload["key"], source="pkce", account=str(payload.get("user_id") or ""))

    def exchange(self, code: str, verifier: str) -> dict:
        """POST the code + verifier to the auth origin and return the parsed response."""
        url = self.origins.exchange_url()
        try:
            response = self.session.post(
                url,
                json={"code": code, "code_verifier": verifier, "code_challenge_method": "S256"},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise AuthNetworkError(f"could not reach the OrcaRouter auth origin: {type(exc).__name__}") from None

        status = getattr(response, "status_code", 0)
        if status == 200:
            try:
                payload = response.json()
            except ValueError:
                raise AuthNetworkError("the OrcaRouter auth origin returned a non-JSON response") from None
            if not isinstance(payload, dict) or not payload.get("key"):
                raise AuthNetworkError("the OrcaRouter auth response did not contain a key")
            return payload
        if status == 400:
            raise ChallengeRejected(
                "OrcaRouter refused the code challenge method. Nothing was stored; retry the login."
            )
        if status == 403:
            raise ExchangeRejected(
                "The authorization code was unknown, expired or already used, or the verifier did not "
                "match. Start a new `wintermute-orcarouter login` (codes are single-use, 10 minute TTL)."
            )
        if status == 429:
            raise RateLimited(
                "This account has reached the OrcaRouter limit for authorizations (10 issued keys per "
                "24 hours). Reuse the existing key or wait before trying again."
            )
        raise AuthNetworkError(f"the OrcaRouter auth origin answered HTTP {status}")

    # -- Flow A ---------------------------------------------------------------------
    def _loopback_code(self, challenge: str, state: str) -> str:
        """Flow A: listen on 127.0.0.1, open the browser, receive the code on the socket."""
        result: dict[str, str] = {}
        done = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib API
                parsed = urlsplit(self.path)
                if parsed.path != CALLBACK_PATH:
                    self.send_response(404)
                    self.end_headers()
                    return
                params = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
                # The query is never logged: the default access log would write the code to stderr.
                if not hmac.compare_digest(params.get("state", ""), state):
                    result["error"] = "state_mismatch"
                elif params.get("error"):
                    result["error"] = params["error"]
                elif params.get("code"):
                    result["code"] = params["code"]
                else:
                    result["error"] = "missing_code"

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if params.get("error") or result.get("error") == "state_mismatch":
                    self.wfile.write(
                        b"<p>Authorization was not completed. You can close this tab and retry.</p>"
                    )
                else:
                    self.wfile.write(b"<p>Connected. You can close this tab and return to the terminal.</p>")
                done.set()

            def log_message(self, *args):  # silence the access log (no code in stderr)
                return

        server = HTTPServer((LOOPBACK_HOST, 0), Handler)
        server.timeout = 0.5
        port = server.server_address[1]
        thread = threading.Thread(target=self._serve_until_done, args=(server, done), daemon=True)
        thread.start()
        try:
            callback_url = f"http://{LOOPBACK_HOST}:{port}{CALLBACK_PATH}"
            url = build_authorize_url(
                self.origins,
                callback_url=callback_url,
                challenge=challenge,
                state=state,
                app_name=self.app_name,
                scope=self.scope,
            )
            self._open(url)
            deadline = time.monotonic() + self.timeout
            while not done.is_set() and time.monotonic() < deadline:
                done.wait(0.25)
            if not done.is_set():
                raise AuthorizationTimeout(
                    "Timed out waiting for the OrcaRouter consent screen. No credential was stored; "
                    "run the login again."
                )
        finally:
            # ``shutdown()`` waits for a ``serve_forever`` loop that this flow never uses;
            # closing the listening socket is what releases the handler thread.
            server.server_close()
            thread.join(timeout=2)

        if result.get("error") == "state_mismatch":
            raise StateMismatch("The OAuth callback did not match this login attempt (state mismatch).")
        if result.get("error") in ("access_denied", "denied"):
            raise AuthorizationDenied("Authorization was denied on the OrcaRouter consent screen.")
        if result.get("error"):
            raise PkceError(f"Authorization failed: {result['error']}")
        return result["code"]

    @staticmethod
    def _serve_until_done(server: HTTPServer, done: threading.Event) -> None:
        try:
            while not done.is_set():
                server.handle_request()
        except (OSError, ValueError):
            # The listening socket was closed by the flow (timeout/cancel); stop serving.
            return

    # -- Flow B ---------------------------------------------------------------------
    def _oob_code(self, challenge: str, state: str) -> str:
        """Flow B: the consent screen shows a code which the user pastes back."""
        url = build_authorize_url(
            self.origins,
            callback_url="oob",
            challenge=challenge,
            state=state,
            app_name=self.app_name,
            scope=self.scope,
        )
        self._open(url, show_only_hint=True)
        code = self.prompt("Paste the authorization code shown by OrcaRouter: ").strip()
        if not code:
            raise AuthorizationDenied("No authorization code was entered; nothing was stored.")
        return code

    # -- helpers ----------------------------------------------------------------------
    def _open(self, url: str, *, show_only_hint: bool = False) -> None:
        self.out("")
        self.out("Opening the OrcaRouter consent screen. If your browser does not open, visit:")
        self.out(url)
        self.out("")
        opener = self.opener if self.opener is not None else webbrowser.open
        try:
            opener(url)
        except Exception:  # noqa: BLE001 - a missing browser must not abort the flow
            if not show_only_hint:
                self.out("(could not open a browser automatically; use the URL above)")
