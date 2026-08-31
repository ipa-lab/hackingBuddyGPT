import asyncio

import pytest

import hackingBuddyGPT.utils.connectors.local_shell as local_shell
from hackingBuddyGPT.capabilities.ssh_test_credential import SSHTestCredential
from hackingBuddyGPT.utils.connectors.local_shell import LocalShellConnection
from hackingBuddyGPT.utils.shell_root_detection import (
    ROOT_PROOF_DIR,
    ROOT_PROOF_PATH,
    new_root_proof_challenge,
    root_proof_challenge_matches,
    root_proof_cleanup_script,
    root_proof_install_script,
    strip_ansi,
)


def test_root_proof_challenge_is_nonce_bound():
    command, digest = new_root_proof_challenge("proof-value")
    second_command, _ = new_root_proof_challenge("proof-value")

    assert "proof-value" not in command
    assert ROOT_PROOF_PATH in command
    assert command != second_command
    assert root_proof_challenge_matches(f"{digest}  -", digest)
    assert not root_proof_challenge_matches("wrong", digest)


def test_root_proof_is_installed_root_only():
    proof = "target-root-proof"

    script = root_proof_install_script(proof)
    assert script.splitlines() == [
        "set -eu",
        f"/usr/bin/install -d -m 0700 {ROOT_PROOF_DIR}",
        f"printf '%s' {proof} | /usr/bin/install -m 0600 /dev/stdin {ROOT_PROOF_PATH}",
    ]
    assert root_proof_cleanup_script() == f"/bin/rm -f {ROOT_PROOF_PATH}"


def test_strip_ansi():
    assert strip_ansi("\x1b[01;31mred\x1b[0m") == "red"
    assert strip_ansi(None) == ""


def test_is_admin_from_whoami():
    from hackingBuddyGPT.utils.shell_root_detection import is_admin_from_whoami

    # running as SYSTEM
    assert is_admin_from_whoami("nt authority\\system") is True
    assert is_admin_from_whoami("NT AUTHORITY\\SYSTEM") is True
    # enabled Administrators-group membership (SID S-1-5-32-544)
    assert is_admin_from_whoami("BUILTIN\\Administrators S-1-5-32-544 Enabled group, Group owner") is True
    # filtered token: Administrators present but "deny only" -> not elevated
    assert is_admin_from_whoami("BUILTIN\\Administrators S-1-5-32-544 Group used for deny only") is False
    # a plain low-priv user
    assert is_admin_from_whoami("myhost\\alice S-1-5-21-1000 Mandatory group, Enabled") is False


def test_check_windows_admin_success():
    from hackingBuddyGPT.utils.shell_root_detection import (
        LOGIN_AS_ROOT_SUCCESSFUL,
        check_windows_admin_success,
    )

    # credential-test path reuses the shared success message
    assert check_windows_admin_success("test_credential admin hunter2", LOGIN_AS_ROOT_SUCCESSFUL) is True
    assert check_windows_admin_success("test_credential admin wrong", "Authentication error\n") is False
    # command path: whoami output showing SYSTEM / Administrators
    assert check_windows_admin_success("whoami", "nt authority\\system") is True
    assert check_windows_admin_success("whoami /groups", "BUILTIN\\Administrators S-1-5-32-544 Enabled group") is True
    assert check_windows_admin_success("whoami", "myhost\\alice") is False


@pytest.mark.parametrize(
    ("command_uid", "uid_after_challenge", "expected_verified"),
    [(0, 0, True), (0, 1000, False), (1000, None, False)],
    ids=["stays-root", "drops-uid", "root-looking-output"],
)
def test_local_shell_requires_root_before_and_after_challenge(
    monkeypatch, command_uid, uid_after_challenge, expected_verified
):
    conn = LocalShellConnection(tmux_session="unused")
    conn._initialized = True
    conn._root_proof = "proof"

    def run(command):
        conn.last_uid = command_uid if command == "id" else uid_after_challenge
        return {"id": "uid=0(root)", "challenge": "digest  -"}[command]

    conn.run_with_unique_markers = run
    monkeypatch.setattr(local_shell, "new_root_proof_challenge", lambda proof: ("challenge", "digest"))

    assert conn.run("id") == ("uid=0(root)", "", 0)
    assert conn.root_verified is expected_verified


def test_local_shell_clears_stale_root():
    conn = LocalShellConnection(tmux_session="unused")
    conn._initialized = True
    conn.root_verified = True
    conn.last_uid = 0

    assert conn.run(" ") == ("", "", 0)
    assert conn.root_verified is False
    assert conn.last_uid is None


class _FakeLegacySSHConnection:
    def __init__(self):
        self.root_verified = True
        self.keyfilename = "/configured/key"

    def new_with(self, **kwargs):
        return self

    def init(self):
        pass


def test_legacy_credential_sets_root_only_for_root_login():
    conn = _FakeLegacySSHConnection()

    result = asyncio.run(SSHTestCredential(conn=conn)("lowpriv", "trustno1"))

    assert result == "Authentication successful, but user lowpriv is not root\n"
    assert conn.root_verified is False
    assert conn.keyfilename == ""

    result = asyncio.run(SSHTestCredential(conn=conn)("root", "s3cret"))
    assert result == "Login as root was successful\n"
    assert conn.root_verified is True
