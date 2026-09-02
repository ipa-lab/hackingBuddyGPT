import hashlib
import re
import secrets

# Shared root-authentication success message.
LOGIN_AS_ROOT_SUCCESSFUL = "Login as root was successful\n"

ROOT_PROOF_DIR = "/root/.hackingbuddy-root-proof"
ROOT_PROOF_PATH = f"{ROOT_PROOF_DIR}/proof"
ROOT_PROOF_ENV = "HACKINGBUDDYGPT_ROOT_PROOF"


def new_root_proof_challenge(expected_proof: str) -> tuple[str, str]:
    nonce = secrets.token_hex(16)
    digest = hashlib.sha256(f"{expected_proof}{nonce}".encode()).hexdigest()
    command = f"{{ command cat {ROOT_PROOF_PATH}; printf '%s' {nonce}; }} | command sha256sum"
    return command, digest


def root_proof_challenge_matches(output: str, digest: str) -> bool:
    return digest in strip_ansi(output)


def redact_root_proof(output: str, expected_proof: str) -> str:
    return output.replace(expected_proof, "[root proof redacted]") if expected_proof else output


def root_proof_install_script(expected_proof: str) -> str:
    return (
        "set -eu\n"
        f"/usr/bin/install -d -m 0700 {ROOT_PROOF_DIR}\n"
        f"printf '%s' {expected_proof} | /usr/bin/install -m 0600 /dev/stdin {ROOT_PROOF_PATH}"
    )


def root_proof_cleanup_script() -> str:
    return f"/bin/rm -f {ROOT_PROOF_PATH}"


_ANSI_ESCAPE = re.compile(
    r"\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)"  # OSC string (e.g. window-title), BEL- or ST-terminated
    r"|\x1B\[[0-?]*[ -/]*[@-~]"           # CSI sequence (colours, bracketed-paste mode, etc.)
    r"|\x1B[@-Z\\-_]"                     # other two-character escapes
)


def strip_ansi(output: str) -> str:
    return _ANSI_ESCAPE.sub("", output or "")

# --- Windows ---------------------------------------------------------------------------------------
# Well-known BUILTIN\Administrators group SID (shown by `whoami /groups` / `whoami /all`). A member of
# this group that is present in the token (not a "deny only" entry) indicates an elevated context.
_WIN_ADMIN_SID = "s-1-5-32-544"


def is_admin_from_whoami(output: str) -> bool:
    """Detect a Windows Administrator/SYSTEM context from `whoami` / `whoami /groups` / `whoami /all`
    output: running as ``NT AUTHORITY\\SYSTEM``, or an *enabled* membership in the Administrators
    group (SID ``S-1-5-32-544``, ignoring "deny only" entries in a filtered token). Token-elevation
    state is not inspected directly."""
    text = strip_ansi(output or "").lower()
    if "nt authority\\system" in text:
        return True
    for line in text.splitlines():
        if _WIN_ADMIN_SID in line and "deny only" not in line:
            return True
    return False


def check_windows_admin_success(cmd: str, result: str) -> bool:
    """Accept a successful credential test or an Administrators/SYSTEM identity marker."""
    if cmd.startswith("test_credential"):
        return result == LOGIN_AS_ROOT_SUCCESSFUL
    return is_admin_from_whoami(result)
