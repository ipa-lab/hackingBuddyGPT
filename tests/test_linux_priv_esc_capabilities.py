import asyncio
import hashlib
import re

import pytest

from hackingBuddyGPT.usecases.priv_esc._linux_capabilities import (
    LinuxPrivEscRunCommand,
    LinuxPrivEscTestCredential,
)
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL, ROOT_PROOF_PATH

_PROOF = "target-root-proof"


class _Connection:
    username = "lowpriv"
    password = "trustno1"
    banner = ""

    def __init__(self, command_uid, challenge_uid, proof=_PROOF):
        self.command_uid = command_uid
        self.challenge_uid = challenge_uid
        self.proof = proof
        self.last_uid = None
        self.calls = []

    def execute(self, command, *args, **kwargs):
        self.calls.append(command)
        if ROOT_PROOF_PATH not in command:
            self.last_uid = self.command_uid
            return f"uid=0(root) {_PROOF}", "", 0

        nonce = re.search(r"printf '%s' ([0-9a-f]+)", command).group(1)
        self.last_uid = self.challenge_uid
        digest = hashlib.sha256(f"{self.proof}{nonce}".encode()).hexdigest()
        return f"{digest}  -", "", 0


class _SyncConnection(_Connection):
    def run(self, command, *args, **kwargs):
        return self.execute(command, *args, **kwargs)


class _AsyncConnection(_Connection):
    async def run(self, command, *args, **kwargs):
        await asyncio.sleep(0)
        return self.execute(command, *args, **kwargs)


@pytest.mark.parametrize("connection_type", [_SyncConnection, _AsyncConnection], ids=["sync", "async"])
@pytest.mark.parametrize(
    ("command_uid", "challenge_uid", "proof", "expected"),
    [
        (0, 0, _PROOF, True),
        (0, 1000, _PROOF, False),
        (0, 0, "nested-container-proof", False),
        (1000, None, _PROOF, False),
    ],
    ids=["verified-root", "uid-dropped", "wrong-proof", "spoofed-output"],
)
def test_run_command_verifies_root_and_redacts_secret(connection_type, command_uid, challenge_uid, proof, expected):
    conn = connection_type(command_uid, challenge_uid, proof)
    capability = LinuxPrivEscRunCommand(conn=conn)
    capability._root_proof = _PROOF

    output = asyncio.run(capability("id"))

    assert capability.root_verified is expected
    assert _PROOF not in output
    assert "[root proof redacted]" in output
    assert len(conn.calls) == (2 if command_uid == 0 else 1)


def test_run_command_keeps_command_and_challenge_together():
    conn = _AsyncConnection(0, 0)
    capability = LinuxPrivEscRunCommand(conn=conn)
    capability._root_proof = _PROOF

    async def run_both():
        await asyncio.gather(capability("first"), capability("second"))

    asyncio.run(run_both())

    assert conn.calls[0] == "first"
    assert ROOT_PROOF_PATH in conn.calls[1]
    assert conn.calls[2] == "second"
    assert ROOT_PROOF_PATH in conn.calls[3]


class _CredentialConnection:
    def __init__(self, password):
        self.password = password

    async def test_credential(self, username, password):
        return password == self.password


def test_root_credential_uses_its_own_verification_state():
    completed = []
    capability = LinuxPrivEscTestCredential(
        conn=_CredentialConnection("s3cret"),
        on_root=lambda: completed.append(True),
    )

    assert asyncio.run(capability("lowpriv", "s3cret")) != LOGIN_AS_ROOT_SUCCESSFUL
    assert capability.root_verified is False
    assert asyncio.run(capability("root", "s3cret")) == LOGIN_AS_ROOT_SUCCESSFUL
    assert capability.root_verified is True
    assert completed == [True]
    assert "wrong" in asyncio.run(capability("root", "nope")).lower()
    assert capability.root_verified is False
