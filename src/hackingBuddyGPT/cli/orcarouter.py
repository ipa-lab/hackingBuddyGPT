"""`wintermute-orcarouter` — connect, inspect and disconnect OrcaRouter credentials.

Two explicit authentication choices, matching the two adapters in
``hackingBuddyGPT.utils.orcarouter.credentials``:

* ``wintermute-orcarouter login --api-key`` — paste an existing ``sk-orca-…`` key.
* ``wintermute-orcarouter login`` — OAuth 2.0 + PKCE: Flow A (loopback) by default,
  ``--oob`` for hosts without a callback listener.

``models`` lists the live catalog for a capability; ``--select`` is the interactive model
picker used instead of typing a model id by hand.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from hackingBuddyGPT.utils.orcarouter.catalog import CAPABILITIES
from hackingBuddyGPT.utils.orcarouter.config import OriginError, Origins
from hackingBuddyGPT.utils.orcarouter.credentials import DotEnvCredentialStore, redact
from hackingBuddyGPT.utils.orcarouter.pkce import PkceError, PkceFlow
from hackingBuddyGPT.utils.orcarouter.provider import (
    AUTHORIZED_APPS_URL,
    KEYS_URL,
    RECOMMENDED_CYBER_MODEL,
    OrcaRouterProvider,
)


def _add_origin_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-base", default="", help="override the inference base URL")
    parser.add_argument("--auth-base", default="", help="override the authentication origin")
    parser.add_argument("--base-url", default="", help="shared self-hosted base for both origins")
    parser.add_argument("--env-file", default=".env", help="secret file that stores ORCA_KEY")


def _origins(args) -> Origins:
    try:
        return Origins.resolve(
            auth_base=args.auth_base or None,
            api_base=args.api_base or None,
            shared=args.base_url or None,
        )
    except OriginError as exc:
        raise SystemExit(f"invalid origin: {exc}") from None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wintermute-orcarouter",
        description="Manage the OrcaRouter provider credentials and model catalog.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="authorize this machine (OAuth 2.0 + PKCE) or store an API key")
    login.add_argument(
        "--api-key",
        action="store_true",
        help="paste an existing sk-orca-… key instead of starting the browser authorization",
    )
    login.add_argument("--oob", action="store_true", help="use Flow B (out-of-band code) instead of loopback")
    login.add_argument("--force", action="store_true", help="re-authorize even if a key is already stored")
    login.add_argument("--app-name", default="hackingBuddyGPT", help="label shown on the consent screen")
    _add_origin_args(login)

    logout = sub.add_parser("logout", help="remove the stored OrcaRouter credential")
    logout.add_argument("--env-file", default=".env", help="secret file that stores ORCA_KEY")

    status = sub.add_parser("status", help="show which credential is in force (masked)")
    status.add_argument("--env-file", default=".env", help="secret file that stores ORCA_KEY")

    models = sub.add_parser("models", help="list or select from the live OrcaRouter model catalog")
    models.add_argument("--capability", choices=CAPABILITIES, default="chat", help="capability to list")
    models.add_argument(
        "--modalities",
        default="",
        help="comma separated input modalities the entry point needs, e.g. image (chat only)",
    )
    models.add_argument("--json", action="store_true", help="emit machine readable JSON")
    models.add_argument("--select", action="store_true", help="interactively pick one model")
    models.add_argument("--model", default="", help="validate one model id against the catalog")
    _add_origin_args(models)

    return parser


def _provider(args, *, mode: str = "auto") -> OrcaRouterProvider:
    return OrcaRouterProvider(
        api_base=args.api_base or None,
        auth_base=args.auth_base or None,
        shared_base=args.base_url or None,
        dotenv_path=args.env_file,
        credential_mode=mode,
    )


def cmd_login(args) -> int:
    store = DotEnvCredentialStore(args.env_file)
    origins = _origins(args)

    if args.api_key:
        key = getpass.getpass("OrcaRouter API key (sk-orca-…): ").strip()
        if not key:
            print("no key entered; nothing was stored", file=sys.stderr)
            return 1
        store.save(key)
        print(f"stored OrcaRouter API key {redact(key)} in {args.env_file}")
        print(f"manage or revoke keys at {KEYS_URL}")
        return 0

    if store.load() and not args.force:
        print(f"an OrcaRouter credential is already stored in {args.env_file} ({redact(store.load())})")
        print("reuse it, or pass --force to authorize again (10 issued keys per user per 24 hours)")
        return 0

    flow = PkceFlow(origins=origins, app_name=args.app_name)
    try:
        credential = flow.connect(mode="oob" if args.oob else "loopback")
    except PkceError as exc:
        print(f"authorization failed: {exc}", file=sys.stderr)
        return 1
    store.save(credential.value)
    print(f"connected; stored OrcaRouter key {credential.masked} in {args.env_file}")
    print(f"authorized apps are listed at {AUTHORIZED_APPS_URL}")
    return 0


def cmd_logout(args) -> int:
    store = DotEnvCredentialStore(args.env_file)
    existed = bool(store.load())
    store.clear()
    print("removed the stored OrcaRouter credential" if existed else "no stored OrcaRouter credential")
    print("revoke the key itself at " + AUTHORIZED_APPS_URL)
    return 0


def cmd_status(args) -> int:
    provider = _provider(args)
    store = DotEnvCredentialStore(args.env_file)
    stored = store.load()
    try:
        credential = provider.credential()
    except Exception as exc:  # noqa: BLE001 - status must not crash a shell pipeline
        print(f"credential: none ({exc})")
        print("connect with `wintermute-orcarouter login` or set ORCAROUTER_API_KEY")
        return 1
    print(f"credential: {credential.masked} ({credential.source})")
    print(f"stored in {args.env_file}: {'yes' if stored else 'no'}")
    print(f"inference:  {provider.origins.api_base}")
    print(f"auth:       {provider.origins.auth_base}")
    print(f"recommended cyber model: {RECOMMENDED_CYBER_MODEL} (unlocked per workspace after business verification)")
    print(f"key dashboard: {KEYS_URL}")
    return 0


def cmd_models(args) -> int:
    provider = _provider(args)
    modalities = tuple(part.strip() for part in args.modalities.split(",") if part.strip())
    selector = provider.selector(args.capability, modalities)
    result = selector.load()

    if args.model:
        try:
            selector.select(args.model)
        except Exception as exc:  # noqa: BLE001
            print(str(exc), file=sys.stderr)
            return 1

    if args.json:
        print(
            json.dumps(
                {
                    "source": result.source,
                    "degraded": result.degraded,
                    "capability": result.capability,
                    "models": [
                        {
                            "id": model.id,
                            "name": model.name,
                            "context_window": model.context_window,
                            "input_modalities": sorted(model.input_modalities),
                            "endpoint_types": sorted(model.endpoint_types),
                            "reasoning_efforts": list(model.reasoning_efforts),
                        }
                        for model in result.models
                    ],
                },
                indent=2,
            )
        )
        return 0

    if not result.models:
        print(f"no OrcaRouter models offered for capability {args.capability!r} with this credential")
        return 1
    print(f"{len(result.models)} models for capability {args.capability!r} (source: {result.source})")
    for model in result.models:
        context = f"{model.context_window}" if model.context_window else "?"
        modalities_text = "+".join(sorted(model.input_modalities)) or "?"
        print(f"  {model.id:<44} ctx={context:<9} input={modalities_text}")
    if result.degraded:
        print(f"note: live discovery unavailable ({result.detail}); verified fallback shown")

    if args.select:
        try:
            chosen = selector.choose("Select an OrcaRouter model")
        except Exception as exc:  # noqa: BLE001
            print(str(exc), file=sys.stderr)
            return 1
        print(f"\nselected: {chosen}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "login": cmd_login,
        "logout": cmd_logout,
        "status": cmd_status,
        "models": cmd_models,
    }
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        print("interrupted; nothing was stored", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
