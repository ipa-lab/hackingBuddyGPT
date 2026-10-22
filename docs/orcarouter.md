# OrcaRouter provider

[OrcaRouter](https://www.orcarouter.ai) is an OpenAI-compatible AI gateway that routes many
providers behind one endpoint. hackingBuddyGPT ships it as a named provider preset
(`--llm.preset=orcarouter`) with two explicit ways to authenticate, a live model catalog and
capability filters for every entry point.

## Endpoints

| Surface | URL |
|---|---|
| Inference (OpenAI wire format) | `https://api.orcarouter.ai/v1` |
| Model catalog | `GET https://api.orcarouter.ai/v1/models` (Bearer auth, `?capability=…`) |
| Consent screen | `https://www.orcarouter.ai/auth` |
| Code exchange | `POST https://www.orcarouter.ai/api/v1/auth/keys` |
| Key management | `https://www.orcarouter.ai/console/token` |
| Authorized apps | `https://www.orcarouter.ai/console/authorized-apps` |

Authentication and inference use different public origins. The exchange path is
`/api/v1/auth/keys` on the auth origin — **not** `/v1/auth/keys` on the relay, which is a 404.

Both origins are configurable: `ORCA_AUTH_BASE_URL` and `ORCA_API_BASE_URL` (explicit) take
precedence over a shared `ORCA_BASE_URL`; the same values can be passed as `--auth-base`,
`--api-base`, `--base-url` to `wintermute-orcarouter` and as `--llm.preset_auth_base` /
`--llm.preset_api_base` to `wintermute`. Remote origins must be HTTPS; plain HTTP is accepted only
for loopback development.

## Two authentication choices

Both produce an ordinary `sk-orca-…` API key that belongs to the user, and both feed the same
credential seam (`utils/orcarouter/credentials.py`). The request and catalog code never looks at
which adapter produced the key.

| Choice | Command | Credential source |
|---|---|---|
| Existing key | `wintermute-orcarouter login --api-key`, or `--llm.api_key` / `ORCAROUTER_API_KEY` / `ORCA_KEY` | User pastes an `sk-orca-…` key. |
| Account login | `wintermute-orcarouter login` (`--oob` for hosts that cannot listen on loopback) | OAuth 2.0 + PKCE issues the key in the browser. |

Keys are stored in the project's existing secret file, `.env`, under `ORCA_KEY` (mode 0600);
unrelated lines are preserved. `wintermute-orcarouter logout` removes it. Nothing is written to a
new secret store, and keys never appear in logs, error messages, URLs or telemetry.

### OAuth 2.0 + PKCE details

- **Flow A (loopback)** by default: the listener is bound on `127.0.0.1:<ephemeral>` before the
  browser opens, the callback is compared against the `state` with a constant-time comparison, the
  browser gets a "you can close this tab" page, and the listener is closed on success, denial,
  timeout or error.
- **Flow B (out-of-band)** with `--oob`: `callback_url=oob`, the consent screen shows a code and the
  operator pastes it back. Both flows send S256, because a redirected flow can still hand the user a
  code on screen.
- Verifier and state come from `secrets.token_bytes` on every attempt; the challenge is
  `base64url(sha256(verifier))` without padding; the verifier never leaves the process and is never
  logged.
- Exit paths: denial, `state` mismatch, timeout, HTTP 400 (method mismatch), HTTP 403 (unknown,
  expired or reused code / verifier mismatch), HTTP 429 (10 issued keys per user per 24 h), and
  transport errors all end with an actionable message. No hot loop, no credential in the message.
- The granted `scope` in the exchange response is read back and must be `api`; a narrower grant is
  reported instead of being assumed.
- A PKCE-issued key is **durable, not a refresh token**. It is reused until revoked; there is no
  refresh grant. A `401` from the relay marks the credential generation that made the request as
  needing reauthentication — an older generation cannot mark a newly authorized key.
- Flow C (device grant) is not implemented; the CLI has browser (A) and out-of-band (B) paths.

## Model catalog

`GET {api_base}/models?capability=<capability>` is the only source of truth. The response is
bounded (10 s timeout, 4 MiB, 2000 items, strict item shape) and filtered per entry point:

| Entry point | Filter |
|---|---|
| Chat / agent | `capability=chat`, `supported_endpoint_types` must contain `openai`, `anthropic`, `gemini` or `openai-response`; image/video/rerank/embedding-only models are excluded. |
| Multimodal chat | Chat + `architecture.input_modalities` must contain the attached modality (image/audio/video). Undeclared ⇒ excluded. |
| Embedding (RAG) | `capability=embedding` / `embeddings` endpoint type. |
| Image generation | `image-generation` endpoint type. |
| Video generation | `openai-video` endpoint type. |
| Rerank | `jina-rerank` endpoint type. |

When discovery succeeds it is authoritative. When it fails, a small verified fallback catalog
(`utils/orcarouter/catalog.py`) is used and reported as degraded; it is never mixed into a live
result. A previously selected model that no longer matches the current capability/modality is
dropped and the operator is told to pick again.

The model control is the catalog itself: `wintermute-orcarouter models [--select]`, or an
interactive picker when a preset run has no `--llm.model` on a TTY. For non-interactive runs, an
unset or unoffered model is an error listing the compatible ids.

`orcacyber-zero` (OrcaCyber Zero) is the recommended model for security work: it is available to
security teams that have completed business verification and is permitted for authorized security
testing, where general-purpose gateways often refuse such requests. Until it is enabled for a
workspace the default falls back to `orcarouter/fusion`.

## Credential lifecycle

- `wintermute-orcarouter status` shows which credential is in force (masked), where it is stored and
  which origins are used.
- The user can revoke every key issued to this app at
  <https://www.orcarouter.ai/console/authorized-apps>; individual keys are managed at
  <https://www.orcarouter.ai/console/token>.
- A revoked key produces a terminal `401`: the provider marks that exact credential generation for
  reauthentication and tells the operator to run `wintermute-orcarouter login`. It does not attempt
  a fake refresh and does not delete the stored key before a successful replacement.
- A key that may not use a specific model produces `403 model_access_denied`, surfaced with the
  console link and the model picker instead of being retried.

## Primary sources

- Product and endpoint documentation: <https://www.orcarouter.ai/docs>
- Provider home / legal entity and terms: <https://www.orcarouter.ai> ·
  <https://www.orcarouter.ai/terms>
- Authorization and revocation console: <https://www.orcarouter.ai/console/token> ·
  <https://www.orcarouter.ai/console/authorized-apps>
- Catalog verified live on 2026-10-22 against `https://api.orcarouter.ai/v1/models`.
- Maintenance owner for this integration: OrcaRouter engineering team (see the PR disclosure).
