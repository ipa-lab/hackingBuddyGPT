"""Credential seam tests: API key adapter, PKCE adapter, origins and terminal 401 handling."""

import io
import os
import stat
import tempfile
import threading
import unittest
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from hackingBuddyGPT.utils.orcarouter.catalog import CatalogResult, ModelInfo
from hackingBuddyGPT.utils.orcarouter.config import OriginError, Origins
from hackingBuddyGPT.utils.orcarouter.credentials import (
    ApiKeyCredentialSource,
    Credential,
    CredentialState,
    DotEnvCredentialStore,
    MissingCredentialError,
    PkceCredentialSource,
    ReauthenticationRequired,
    acquire_credential,
    redact,
)
from hackingBuddyGPT.utils.orcarouter.pkce import (
    AuthNetworkError,
    AuthorizationDenied,
    AuthorizationTimeout,
    ChallengeRejected,
    ExchangeRejected,
    PkceFlow,
    RateLimited,
    ScopeDowngrade,
    StateMismatch,
    build_authorize_url,
    create_pkce_pair,
    create_state,
)
from hackingBuddyGPT.utils.orcarouter.provider import OrcaRouterProvider

TEST_KEY = "sk-orca-test-0000000000"


class FakeResponse:
    def __init__(self, status_code, payload=None, *, invalid_json=False):
        self.status_code = status_code
        self._payload = payload
        self._invalid_json = invalid_json

    def json(self):
        if self._invalid_json:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    def __init__(self, response=None):
        self.response = response
        self.posts = []

    def post(self, url, json=None, timeout=None):  # noqa: A002 - requests signature
        self.posts.append({"url": url, "json": json, "timeout": timeout})
        return self.response


class RecordingFlow:
    """A PKCE flow double that records invocations."""

    def __init__(self, credential=None, error=None):
        self.credential = credential or Credential(TEST_KEY, "pkce", account="u1")
        self.error = error
        self.calls = 0

    def connect(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.credential


def _flow(session=None, **kwargs):
    return PkceFlow(origins=Origins.resolve(env={}), session=session or FakeSession(), out=lambda _: None, **kwargs)


class TestCredentialStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".env"
        self.store = DotEnvCredentialStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_load_clear(self):
        self.store.save(TEST_KEY)
        self.assertEqual(self.store.load(), TEST_KEY)
        self.assertTrue(self.store.exists())
        self.store.clear()
        self.assertIsNone(self.store.load())
        self.assertFalse(self.store.exists())

    def test_preserves_unrelated_lines(self):
        self.path.write_text("llm.model='gpt-4o'\n# comment\n")
        self.store.save(TEST_KEY)
        text = self.path.read_text()
        self.assertIn("llm.model='gpt-4o'", text)
        self.assertIn("# comment", text)
        self.assertIn("ORCA_KEY=", text)
        self.store.save("sk-orca-second-0000")
        self.assertEqual(self.path.read_text().count("ORCA_KEY="), 1)

    def test_file_is_private(self):
        self.store.save(TEST_KEY)
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode, 0o600)

    def test_redaction_never_reveals_the_key(self):
        masked = redact(TEST_KEY)
        self.assertNotIn("0000000000", masked)
        self.assertTrue(masked.endswith(TEST_KEY[-4:]))

    def test_repr_never_reveals_the_key(self):
        credential = Credential(TEST_KEY, "api_key")
        self.assertNotIn(TEST_KEY, repr(credential))


class TestApiKeyAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DotEnvCredentialStore(Path(self.tmp.name) / ".env")

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_key_wins(self):
        source = ApiKeyCredentialSource("sk-orca-explicit", self.store, env={"ORCAROUTER_API_KEY": "sk-orca-env"})
        self.assertEqual(source.acquire().value, "sk-orca-explicit")
        self.assertEqual(source.acquire().source, "api_key")

    def test_environment_then_store(self):
        source = ApiKeyCredentialSource(None, self.store, env={"ORCA_KEY": "sk-orca-env2"})
        self.assertEqual(source.acquire().value, "sk-orca-env2")
        self.store.save("sk-orca-stored")
        source = ApiKeyCredentialSource(None, self.store, env={})
        self.assertEqual(source.acquire().value, "sk-orca-stored")

    def test_missing_key_is_actionable(self):
        source = ApiKeyCredentialSource(None, self.store, env={})
        with self.assertRaises(MissingCredentialError) as ctx:
            source.acquire()
        self.assertIn("wintermute-orcarouter login", str(ctx.exception))


class TestPkcePrimitives(unittest.TestCase):
    def test_verifier_and_state_are_fresh(self):
        pairs = {create_pkce_pair()[0] for _ in range(20)}
        self.assertEqual(len(pairs), 20)
        self.assertEqual(len({create_state() for _ in range(20)}), 20)

    def test_challenge_is_unpadded_sha256_of_verifier(self):
        import base64
        import hashlib

        verifier, challenge = create_pkce_pair()
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        self.assertEqual(challenge, expected)
        self.assertNotIn("=", challenge)

    def test_authorize_url_targets_auth_origin_and_omits_verifier(self):
        verifier, challenge = create_pkce_pair()
        origins = Origins.resolve(env={})
        url = build_authorize_url(
            origins, callback_url="oob", challenge=challenge, state="st", app_name="hackingBuddyGPT"
        )
        self.assertTrue(url.startswith("https://www.orcarouter.ai/auth?"))
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("callback_url=oob", url)
        self.assertNotIn(verifier, url)
        self.assertNotIn("api.orcarouter.ai", url)


class TestOrigins(unittest.TestCase):
    def test_public_defaults_are_separate_origins(self):
        origins = Origins.resolve(env={})
        self.assertEqual(origins.auth_base, "https://www.orcarouter.ai")
        self.assertEqual(origins.api_base, "https://api.orcarouter.ai/v1")
        self.assertEqual(origins.exchange_url(), "https://www.orcarouter.ai/api/v1/auth/keys")
        self.assertNotEqual(origins.exchange_url(), origins.api_base + "/auth/keys")

    def test_explicit_overrides_win_and_are_not_derived(self):
        origins = Origins.resolve(
            auth_base="https://auth.self.example",
            api_base="https://relay.self.example/v1",
            env={"ORCA_BASE_URL": "https://ignored.example"},
        )
        self.assertEqual(origins.auth_base, "https://auth.self.example")
        self.assertEqual(origins.api_base, "https://relay.self.example/v1")

    def test_shared_base_covers_both(self):
        origins = Origins.resolve(env={"ORCA_BASE_URL": "https://orca.self.example"})
        self.assertEqual(origins.auth_base, "https://orca.self.example")
        self.assertEqual(origins.api_base, "https://orca.self.example/v1")

    def test_http_allowed_only_for_loopback(self):
        self.assertEqual(
            Origins.resolve(auth_base="http://127.0.0.1:8080", env={}).auth_base, "http://127.0.0.1:8080"
        )
        with self.assertRaises(OriginError):
            Origins.resolve(auth_base="http://auth.example.com", env={})

    def test_userinfo_and_fragment_rejected(self):
        with self.assertRaises(OriginError):
            Origins.resolve(api_base="https://user:pass@api.example.com/v1", env={})
        with self.assertRaises(OriginError):
            Origins.resolve(api_base="https://api.example.com/v1#frag", env={})


class TestExchange(unittest.TestCase):
    def test_success_uses_auth_origin_and_json_body(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "user_id": "42", "scope": "api"}))
        flow = _flow(session)
        payload = flow.exchange("the-code", "the-verifier")
        self.assertEqual(payload["key"], TEST_KEY)
        post = session.posts[0]
        self.assertEqual(post["url"], "https://www.orcarouter.ai/api/v1/auth/keys")
        self.assertNotEqual(post["url"], "https://api.orcarouter.ai/v1/auth/keys")
        self.assertEqual(post["json"]["code_verifier"], "the-verifier")
        self.assertEqual(post["json"]["code_challenge_method"], "S256")

    def test_error_statuses_are_classified_without_leaking_secrets(self):
        cases = [
            (400, ChallengeRejected),
            (403, ExchangeRejected),
            (429, RateLimited),
            (500, AuthNetworkError),
        ]
        for status, expected in cases:
            with self.subTest(status=status):
                flow = _flow(FakeSession(FakeResponse(status)))
                with self.assertRaises(expected) as ctx:
                    flow.exchange("the-code", "the-verifier")
                self.assertNotIn("the-verifier", str(ctx.exception))
                self.assertNotIn("the-code", str(ctx.exception))

    def test_network_failure_does_not_hot_loop(self):
        class Broken:
            def post(self, *args, **kwargs):
                import requests

                raise requests.ConnectionError("boom")

        flow = _flow(Broken())
        with self.assertRaises(AuthNetworkError):
            flow.exchange("c", "v")

    def test_scope_downgrade_is_rejected(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "user_id": "42", "scope": "connector"}))
        flow = _flow(session)
        with patch.object(PkceFlow, "_loopback_code", return_value="code"):
            with self.assertRaises(ScopeDowngrade):
                flow.connect()


class TestFlowA(unittest.TestCase):
    def _opener(self, results):
        def opener(url):
            from urllib.parse import parse_qs, urlsplit

            query = parse_qs(urlsplit(url).query)
            callback = query["callback_url"][0]
            state = query["state"][0]

            def deliver():
                try:
                    with urllib.request.urlopen(f"{callback}?code=one-time-code&state={state}", timeout=5) as r:
                        results.append(r.status)
                except Exception as exc:  # noqa: BLE001
                    results.append(exc)

            threading.Thread(target=deliver, daemon=True).start()
            return True

        return opener

    def test_loopback_delivers_code_and_returns_credential(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "user_id": "42", "scope": "api"}))
        seen = []
        flow = _flow(session, opener=self._opener(seen), timeout=10)
        credential = flow.connect(mode="loopback")
        self.assertEqual(credential.value, TEST_KEY)
        self.assertEqual(credential.source, "pkce")
        self.assertEqual(credential.account, "42")
        self.assertEqual(seen, [200])

    def test_state_mismatch_is_rejected(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "scope": "api"}))

        def opener(url):
            from urllib.parse import parse_qs, urlsplit

            callback = parse_qs(urlsplit(url).query)["callback_url"][0]

            def deliver():
                try:
                    urllib.request.urlopen(f"{callback}?code=stolen&state=wrong-state", timeout=5).read()
                except Exception:  # noqa: BLE001
                    pass

            threading.Thread(target=deliver, daemon=True).start()
            return True

        flow = _flow(session, opener=opener, timeout=10)
        with self.assertRaises(StateMismatch):
            flow.connect(mode="loopback")
        self.assertEqual(session.posts, [])  # no code was exchanged

    def test_denial_is_reported(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "scope": "api"}))

        def opener(url):
            from urllib.parse import parse_qs, urlsplit

            query = parse_qs(urlsplit(url).query)
            callback, state = query["callback_url"][0], query["state"][0]

            def deliver():
                try:
                    urllib.request.urlopen(f"{callback}?error=access_denied&state={state}", timeout=5).read()
                except Exception:  # noqa: BLE001
                    pass

            threading.Thread(target=deliver, daemon=True).start()
            return True

        flow = _flow(session, opener=opener, timeout=10)
        with self.assertRaises(AuthorizationDenied):
            flow.connect(mode="loopback")
        self.assertEqual(session.posts, [])

    def test_timeout_ends_cleanly(self):
        flow = _flow(FakeSession(), opener=lambda url: True, timeout=0.2)
        with self.assertRaises(AuthorizationTimeout):
            flow.connect(mode="loopback")


class TestFlowB(unittest.TestCase):
    def test_out_of_band_code_is_exchanged(self):
        session = FakeSession(FakeResponse(200, {"key": TEST_KEY, "user_id": "7", "scope": "api"}))
        flow = _flow(session, opener=lambda url: True, prompt=lambda _: "pasted-code", timeout=5)
        credential = flow.connect(mode="oob")
        self.assertEqual(credential.value, TEST_KEY)
        self.assertEqual(session.posts[0]["url"], "https://www.orcarouter.ai/api/v1/auth/keys")

    def test_empty_code_is_a_denial(self):
        flow = _flow(FakeSession(), opener=lambda url: True, prompt=lambda _: "  ", timeout=5)
        with self.assertRaises(AuthorizationDenied):
            flow.connect(mode="oob")


class TestDualAdapters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DotEnvCredentialStore(Path(self.tmp.name) / ".env")

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_adapters_yield_the_same_credential_shape(self):
        api_key = ApiKeyCredentialSource(TEST_KEY, self.store, env={}).acquire()
        flow = RecordingFlow()
        pkce = PkceCredentialSource(self.store, lambda: flow).acquire(force=True)
        self.assertEqual(type(api_key), type(pkce))
        self.assertEqual(api_key.value, pkce.value)
        self.assertEqual({api_key.source, pkce.source}, {"api_key", "pkce"})

    def test_downstream_ignores_credential_source(self):
        provider = OrcaRouterProvider(env={}, store=self.store, flow_factory=lambda: RecordingFlow())
        api_key = Credential(TEST_KEY, "api_key")
        pkce = Credential(TEST_KEY, "pkce", account="u1")
        self.assertEqual(provider.completion_kwargs("google/gemini-3.5-flash", api_key),
                         provider.completion_kwargs("google/gemini-3.5-flash", pkce))

    def test_pkce_credential_is_persisted_and_reused(self):
        flow = RecordingFlow()
        source = PkceCredentialSource(self.store, lambda: flow)
        source.acquire(force=True)
        self.assertEqual(self.store.load(), TEST_KEY)
        source.acquire()
        self.assertEqual(flow.calls, 1)  # second call reused the stored key

    def test_failed_login_keeps_the_old_secret(self):
        self.store.save("sk-orca-old-key")
        source = PkceCredentialSource(self.store, lambda: RecordingFlow(error=AuthorizationDenied("denied")))
        with self.assertRaises(AuthorizationDenied):
            source.acquire(force=True)
        self.assertEqual(self.store.load(), "sk-orca-old-key")


class TestTerminalUnauthorized(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DotEnvCredentialStore(Path(self.tmp.name) / ".env")
        self.store.save(TEST_KEY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_revoked_key_marks_needs_reauth_without_refresh(self):
        state = CredentialState()
        provider = OrcaRouterProvider(env={}, store=self.store, flow_factory=lambda: RecordingFlow())
        credential = acquire_credential(
            explicit_api_key=None, store=self.store, flow_factory=lambda: RecordingFlow(), state=state
        )
        provider._credential = credential
        provider._state = state

        class Unauthorized(Exception):
            status_code = 401

        with self.assertRaises(ReauthenticationRequired):
            provider.check_response_error(Unauthorized("401"))
        self.assertTrue(state.needs_reauth)
        self.assertEqual(self.store.load(), TEST_KEY)  # not silently deleted
        self.assertFalse(hasattr(provider, "refresh"))  # there is no refresh grant to call

    def test_stale_generation_cannot_poison_a_new_login(self):
        state = CredentialState()
        first = state.issue(Credential(TEST_KEY, "pkce", account="u1"))
        state.mark_unauthorized(first.generation)
        self.assertTrue(state.needs_reauth)

        second = state.issue(Credential("sk-orca-newer-key", "pkce", account="u1"))
        self.assertFalse(state.needs_reauth)
        self.assertFalse(state.mark_unauthorized(first.generation))  # late failure ignored
        self.assertFalse(state.needs_reauth)
        self.assertEqual(second.generation, 2)


class TestSecretsNeverLeak(unittest.TestCase):
    def test_flow_output_and_errors_do_not_contain_the_key_or_verifier(self):
        session = FakeSession(FakeResponse(403))
        stdout, stderr = io.StringIO(), io.StringIO()
        flow = PkceFlow(
            origins=Origins.resolve(env={}),
            session=session,
            out=lambda text: stdout.write(text + "\n"),
            opener=lambda url: True,
        )
        with patch.object(PkceFlow, "_oob_code", return_value="secret-code"):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(ExchangeRejected) as ctx:
                    flow.connect(mode="oob")
        combined = stdout.getvalue() + stderr.getvalue() + str(ctx.exception)
        self.assertNotIn("secret-code", combined)
        self.assertNotIn("sk-orca", combined)


if __name__ == "__main__":
    unittest.main()
