import asyncio
import hashlib
import re

import pytest

import hackingBuddyGPT.utils.connectors.ssh_interactive_connection as ssh_interactive
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection
from hackingBuddyGPT.utils.shell_root_detection import ROOT_PROOF_PATH


class FakeShell:
    """Minimal stand-in for an asyncssh interactive process.

    Acts as both ``stdin`` (``write``) and ``stdout`` (``read``): it echoes typed lines like a PTY,
    expands the marker's status, identity and root-proof probes, and can require a password before
    running a ``sudo`` command. When it has nothing queued, ``read`` blocks so the connector's idle
    detection fires.
    """

    def __init__(
        self,
        *,
        user,
        responses,
        prompt="alice@box:~$ ",
        sudo_password=None,
        root_proof="",
        uid_after_proof=None,
    ):
        self.user, self.prompt = user, prompt
        self.uid = 0 if user == "root" else 1000
        self.responses = responses
        self.sudo_password = sudo_password
        self.root_proof = root_proof
        self.uid_after_proof = uid_after_proof
        self.writes = []
        self._queue = []
        self._awaiting_password_for = None

    # --- stdin side -------------------------------------------------------
    @property
    def stdin(self):
        return self

    @property
    def stdout(self):
        return self

    def write(self, data: str):
        self.writes.append(data)
        line = data.rstrip("\n")

        if self._awaiting_password_for is not None:
            # this write is the password answer
            cmd = self._awaiting_password_for
            self._awaiting_password_for = None
            if self.sudo_password is not None and line == self.sudo_password:
                self._run(cmd)
            else:
                self._queue.append("Sorry, try again.\n")
            return

        echo = self.prompt + line
        self._queue.append("\n".join(echo[i : i + 200] for i in range(0, len(echo), 200)) + "\n")

        if line.startswith("sudo ") and self.sudo_password is not None:
            self._queue.append(f"[sudo] password for {self.user}: ")
            self._awaiting_password_for = line
            return

        self._run(line)

    def _run(self, line: str):
        if line.startswith("{ command cat "):
            nonce = re.search(r"printf '%s' ([0-9a-f]+)", line).group(1)
            digest = hashlib.sha256(f"{self.root_proof}{nonce}".encode()).hexdigest()
            self._queue.append(f"{digest}  -\n")
            if self.uid_after_proof is not None:
                self.uid = self.uid_after_proof
        elif match := re.search(r"(__CMDEND_[0-9a-f]+__)", line):
            self._queue.append(f"{match.group(1)}:0:{self.uid}\n")
        elif line.startswith("echo "):
            arg = line[len("echo ") :].strip().strip('"').strip("'")
            arg = arg.replace("$?", "0")
            self._queue.append(arg + "\n")
        else:
            key = line[len("sudo ") :] if line.startswith("sudo ") else line
            if key in self.responses:
                self._queue.append(self.responses[key] + "\n")
        # a real PTY prints the next prompt as the prefix of the following command echo (see write),
        # so nothing standalone is queued here.

    # --- stdout side ------------------------------------------------------
    async def read(self, _n: int) -> str:
        if self._queue:
            out, self._queue = "".join(self._queue), []
            return out
        await asyncio.sleep(3600)  # nothing to send: block so the connector sees idle
        return ""


def _make_conn(fake, expected_proof="") -> SSHInteractiveConnection:
    conn = SSHInteractiveConnection(host="h", username="alice", password="hunter2")
    conn._process = fake  # skip the real asyncssh connect
    conn._idle = 0.05  # keep the idle wait short for tests
    conn._root_proof = expected_proof
    return conn


def test_connect_kwargs_disable_agent_and_keys_for_password_auth():
    # Regression: asyncssh must not offer agent/default keys before the password, or the server's
    # MaxAuthTries trips ("Too many authentication failures") and every command silently returns "".
    conn = SSHInteractiveConnection(host="h", username="alice", password="pw")
    kw = conn._connect_kwargs()
    assert kw["agent_path"] is None
    assert kw["client_keys"] == []
    assert kw["password"] == "pw"
    assert kw["known_hosts"] is None

    keyed = SSHInteractiveConnection(host="h", username="alice", password="", keyfilename="/k/id")
    assert keyed._connect_kwargs()["client_keys"] == ["/k/id"]


def test_parse_extracts_body_and_uid():
    conn = SSHInteractiveConnection(host="h", username="alice", password="pw")
    start, end = "__CMDSTART_aaaa1111__", "__CMDEND_bbbb2222__"
    captured = (
        f"alice@box:~$ echo {start}\n"
        f"{start}\n"
        "alice@box:~$ id\n"
        "uid=1000(alice) gid=1000(alice) groups=1000(alice)\n"
        f'alice@box:~$ echo "{end}:$?:$(id -u)"\n'
        f"{end}:0:1000\n"
        "alice@box:~$ "
    )
    end_re = re.compile(re.escape(end) + r":(-?\d+):(-?\d+)")
    body, err, rc = conn._parse(captured, start, end, "id", end_re)

    assert body == "uid=1000(alice) gid=1000(alice) groups=1000(alice)"
    assert rc == 0
    assert conn.last_uid == 1000
    assert conn.root_verified is False


def test_parse_redacts_root_proof_without_complete_framing():
    proof = "target-root-proof"
    conn = SSHInteractiveConnection(host="h", username="alice", password="pw")
    conn._root_proof = proof
    start, end = "__CMDSTART_aaaa1111__", "__CMDEND_bbbb2222__"
    end_re = re.compile(re.escape(end) + r":(-?\d+):(-?\d+)")

    body, _, _ = conn._parse(f"{start}\n{proof}\n", start, end, "cat proof", end_re)

    assert body == "[root proof redacted]"


def test_run_framed_low_priv():
    fake = FakeShell(user="alice", responses={"id": "uid=1000(alice) gid=1000(alice)"})
    conn = _make_conn(fake)

    out, err, rc = asyncio.run(conn._run_framed("id", timeout=2))

    assert out == "uid=1000(alice) gid=1000(alice)"


def test_run_framed_answers_sudo_password():
    fake = FakeShell(
        user="root",
        responses={"id": "uid=0(root) gid=0(root) groups=0(root)"},
        sudo_password="hunter2",
    )
    conn = _make_conn(fake)

    out, _, _ = asyncio.run(conn._run_framed("sudo id", timeout=2))

    assert any(write.rstrip("\n") == "hunter2" for write in fake.writes)
    assert "uid=0(root)" in out
    assert conn.last_uid == 0


@pytest.mark.parametrize(
    ("uid_after_challenge", "expected_verified"),
    [(0, True), (1000, False)],
    ids=["uid-stays-root", "uid-drops"],
)
def test_root_verification_requires_root_through_challenge(uid_after_challenge, expected_verified):
    proof = "target-root-proof"
    fake = FakeShell(
        user="root",
        responses={"id": "uid=0(root) gid=0(root) groups=0(root)"},
        root_proof=proof,
        uid_after_proof=uid_after_challenge,
    )
    conn = _make_conn(fake, proof)

    out, _, _ = asyncio.run(conn.run("id", timeout=2))

    assert "uid=0(root)" in out
    assert conn.root_verified is expected_verified
    assert any(ROOT_PROOF_PATH in write for write in fake.writes)
    assert proof not in "".join(fake.writes)
    assert proof not in repr(conn)
    assert proof not in out
    assert ROOT_PROOF_PATH not in out


def test_nested_root_without_target_proof_is_not_verified():
    fake = FakeShell(
        user="root",
        responses={"id": "uid=0(root)", "true": ""},
        root_proof="nested-container-proof",
    )
    conn = _make_conn(fake, "target-root-proof")

    out, _, _ = asyncio.run(conn.run("id", timeout=2))

    assert out == "uid=0(root)"
    assert conn.root_verified is False


def test_one_shot_command_that_reads_target_proof_is_not_verified():
    proof = "target-root-proof"
    fake = FakeShell(
        user="alice",
        responses={f"cat {ROOT_PROOF_PATH}": proof},
        sudo_password="hunter2",
    )
    conn = _make_conn(fake, proof)

    out, err, rc = asyncio.run(conn.run(f"sudo cat {ROOT_PROOF_PATH}", timeout=2))

    assert proof not in out
    assert "[root proof redacted]" in out
    assert conn.root_verified is False


def test_failed_reconnect_clears_stale_root_proof():
    conn = SSHInteractiveConnection(host="h", username="alice", password="hunter2")
    conn.root_verified = True
    conn.last_uid = 0

    async def fail_to_connect():
        raise ConnectionError("no connection")

    conn._ensure_connected = fail_to_connect

    out, err, rc = asyncio.run(conn.run("id"))

    assert rc == 1
    assert conn.root_verified is False
    assert conn.last_uid is None


def test_credential_uses_a_fresh_connection(monkeypatch):
    class FreshConnection:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fresh = FreshConnection()
    seen = {}

    async def connect(**kwargs):
        seen.update(kwargs)
        return fresh

    monkeypatch.setattr(ssh_interactive.asyncssh, "connect", connect)
    conn = SSHInteractiveConnection(host="h", username="alice", password="hunter2", keyfilename="/configured/key")

    assert asyncio.run(conn.test_credential("root", "s3cret")) is True
    assert fresh.closed is True
    assert seen["password"] == "s3cret"
    assert seen["client_keys"] == []
