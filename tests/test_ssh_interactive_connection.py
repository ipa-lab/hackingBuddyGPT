import asyncio
import re

from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection


class FakeShell:
    """Minimal stand-in for an asyncssh interactive process.

    Acts as both ``stdin`` (``write``) and ``stdout`` (``read``): it echoes typed lines like a PTY,
    "expands" the ``echo`` marker lines (``$?`` / ``$(id -u)`` / ``$(id -un)``), and can require a
    password before running a ``sudo`` command. When it has nothing queued, ``read`` blocks so the
    connector's idle detection fires.
    """

    def __init__(self, *, uid, user, responses, prompt="alice@box:~$ ", sudo_password=None):
        self.uid, self.user, self.prompt = uid, user, prompt
        self.responses = responses
        self.sudo_password = sudo_password
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
                self._run(cmd, echo_input=False)
            else:
                self._queue.append("Sorry, try again.\n")
            return

        self._queue.append(self.prompt + line + "\n")  # PTY echoes the typed line

        if line.startswith("sudo ") and self.sudo_password is not None:
            self._queue.append(f"[sudo] password for {self.user}: ")
            self._awaiting_password_for = line
            return

        self._run(line, echo_input=False)

    def _run(self, line: str, echo_input: bool):
        if line.startswith("echo "):
            arg = line[len("echo "):].strip().strip('"').strip("'")
            arg = arg.replace("$?", "0").replace("$(id -u)", str(self.uid)).replace("$(id -un)", self.user)
            self._queue.append(arg + "\n")
        else:
            key = line[len("sudo "):] if line.startswith("sudo ") else line
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


def _make_conn(fake) -> SSHInteractiveConnection:
    conn = SSHInteractiveConnection(host="h", username="alice", password="hunter2")
    conn._process = fake  # skip the real asyncssh connect
    conn._idle = 0.05  # keep the idle wait short for tests
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


def test_parse_extracts_body_and_identity():
    conn = SSHInteractiveConnection(host="h", username="alice", password="pw")
    start, end = "__CMDSTART_aaaa1111__", "__CMDEND_bbbb2222__"
    captured = (
        f"alice@box:~$ echo {start}\n"
        f"{start}\n"
        "alice@box:~$ id\n"
        "uid=1000(alice) gid=1000(alice) groups=1000(alice)\n"
        f'alice@box:~$ echo "{end}:$?:$(id -u):$(id -un)"\n'
        f"{end}:0:1000:alice\n"
        "alice@box:~$ "
    )
    end_re = re.compile(re.escape(end) + r":(-?\d+):(-?\d+):(\S+)")
    body, err, rc = conn._parse(captured, start, end, "id", end_re)

    assert body == "uid=1000(alice) gid=1000(alice) groups=1000(alice)"
    assert rc == 0
    assert conn.last_uid == 1000
    assert conn.last_user == "alice"


def test_run_framed_low_priv():
    fake = FakeShell(uid=1000, user="alice", responses={"id": "uid=1000(alice) gid=1000(alice)"})
    conn = _make_conn(fake)

    out, err, rc = asyncio.run(conn._run_framed("id", timeout=2))

    assert "uid=1000(alice)" in out
    assert conn.last_uid == 1000


def test_run_framed_sudo_answers_password_and_reports_root():
    fake = FakeShell(
        uid=0,
        user="root",
        responses={"id": "uid=0(root) gid=0(root) groups=0(root)"},
        sudo_password="hunter2",
    )
    conn = _make_conn(fake)

    out, err, rc = asyncio.run(conn._run_framed("sudo id", timeout=2))

    # the connector must have written the password in response to the sudo prompt
    assert any(w.rstrip("\n") == "hunter2" for w in fake.writes)
    assert "uid=0(root)" in out
    assert conn.last_uid == 0


def test_run_reports_root_via_is_root():
    fake = FakeShell(uid=0, user="root", responses={"id -u": "0"})
    conn = _make_conn(fake)

    async def go():
        out, err, rc = await conn.run("id -u", timeout=2)
        assert conn.last_uid == 0
        assert await conn.is_root() is True
        return out

    assert asyncio.run(go()).strip() == "0"
