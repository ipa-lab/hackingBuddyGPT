import asyncio
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple

import asyncssh

from hackingBuddyGPT.utils.configurable import configurable
from hackingBuddyGPT.utils.shell_root_detection import (
    ROOT_PROOF_ENV,
    new_root_proof_challenge,
    redact_root_proof,
    root_proof_challenge_matches,
    strip_ansi,
)

# password prompts we auto-answer so that sudo/su work inside the interactive shell
_PW_PROMPT = re.compile(r"(?:\[sudo\] password for [^:]*:|assword:\s*$|'s [Pp]assword:\s*$)")


@configurable("ssh_interactive", "connects to a remote host over a single persistent interactive SSH shell")
@dataclass
class SSHInteractiveConnection:
    """SSH connector that keeps ONE interactive shell open for the whole run.

    Unlike the Fabric-based :class:`SSHConnection` (which runs every command in a fresh
    ``exec_command`` channel), this connector holds a persistent PTY session, so an escalation that
    drops into an interactive root shell (``sudo su``, ``sudo bash``, an exploit) survives into the
    next command. Each command is framed with unique start/end markers. Root sessions must answer a
    nonce challenge using a root-owned proof installed on the target.
    """

    host: str
    username: str
    password: str
    hostname: str = ""
    keyfilename: str = ""
    port: int = 22
    timeout: int = 10  # per-command timeout in seconds

    banner: str = ""

    # runtime state (not configuration)
    last_uid: Optional[int] = field(default=None, init=False)
    root_verified: bool = field(default=False, init=False)
    _root_proof: str = field(default_factory=lambda: os.environ.get(ROOT_PROOF_ENV, ""), init=False, repr=False)
    # how long the output stream must be quiet before a command is considered finished
    _idle: float = field(default=0.5, init=False, repr=False)
    _conn: Optional[asyncssh.SSHClientConnection] = field(default=None, init=False, repr=False)
    _process: Optional[asyncssh.SSHClientProcess] = field(default=None, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def init(self):
        # The shell is opened lazily on the first run() so the asyncssh connection binds to the event
        # loop that actually drives the use-case. Connecting here would bind it to the throwaway loop
        # that configurable.run_maybe_async spins up during configuration resolution.
        pass

    def new_with(
        self, *, host=None, hostname=None, username=None, password=None, keyfilename=None, port=None
    ) -> "SSHInteractiveConnection":
        return SSHInteractiveConnection(
            host=host or self.host,
            hostname=hostname or self.hostname,
            username=username or self.username,
            password=password or self.password,
            keyfilename=keyfilename or self.keyfilename,
            port=port or self.port,
        )

    def _connect_kwargs(self, username=None, password=None) -> dict:
        kwargs = dict(
            host=self.host,
            port=self.port,
            username=username or self.username,
            known_hosts=None,  # targets are pentest boxes; do not verify host keys
            # Mirror the Fabric connector's look_for_keys=False / allow_agent=False: without this
            # asyncssh offers every agent and default identity key first and trips the server's
            # MaxAuthTries ("Too many authentication failures") before the password is ever tried.
            agent_path=None,
            client_keys=[self.keyfilename] if self.keyfilename else [],
        )
        pw = password if password is not None else self.password
        if pw:
            kwargs["password"] = pw
        return kwargs

    async def _ensure_connected(self):
        if self._process is not None:
            return
        self._conn = await asyncssh.connect(**self._connect_kwargs())
        self._process = await self._conn.create_process(term_type="xterm", term_size=(200, 50))

    async def _reset(self):
        proc, conn = self._process, self._conn
        self._process, self._conn = None, None
        try:
            if proc is not None:
                proc.close()
            if conn is not None:
                conn.close()
        except Exception:
            pass

    async def run(self, cmd: str, *args, **kwargs) -> Tuple[str, str, int]:
        timeout = kwargs.get("timeout", self.timeout)
        async with self._lock:
            self.root_verified = False
            self.last_uid = None
            try:
                await self._ensure_connected()
                result = await self._run_framed(cmd, timeout)
                if self.last_uid == 0 and self._root_proof:
                    command, digest = new_root_proof_challenge(self._root_proof)
                    self.last_uid = None
                    output, _, _ = await self._run_framed(command, timeout)
                    self.root_verified = self.last_uid == 0 and root_proof_challenge_matches(output, digest)
                return result
            except Exception as e:
                # the shell may be wedged (a program still holding the tty) or gone; drop it so the
                # next command reconnects, and surface the error text.
                await self._reset()
                return "", str(e), 1

    async def _run_framed(self, cmd: str, timeout: float) -> Tuple[str, str, int]:
        loop = asyncio.get_running_loop()
        start = f"__CMDSTART_{uuid.uuid4().hex[:8]}__"
        end = f"__CMDEND_{uuid.uuid4().hex[:8]}__"
        stdin, stdout = self._process.stdin, self._process.stdout

        buf: list[str] = []

        # 1) start marker + the command
        stdin.write(f"echo {start}\n")
        stdin.write(cmd + "\n")

        # 2) pump output until the shell goes idle (command finished, or we landed in a new shell
        #    after e.g. `sudo su`), answering a single password prompt if one appears.
        deadline = loop.time() + timeout
        answered = False
        while loop.time() < deadline:
            remaining = deadline - loop.time()
            try:
                chunk = await asyncio.wait_for(stdout.read(65536), timeout=min(self._idle, remaining))
            except asyncio.TimeoutError:
                break  # idle
            if chunk == "":
                raise ConnectionError("interactive SSH shell closed unexpectedly")
            buf.append(chunk)
            if not answered and _PW_PROMPT.search(strip_ansi(chunk)):
                stdin.write(self.password + "\n")
                answered = True

        # 3) capture UID before attempting the root-only proof.
        stdin.write(
            f"r=$?;case $- in *r*)((EUID))||echo {end}:$r:0;;"
            f"*)/usr/bin/printf '{end}:%s:%s\\n' \"$r\" \"$(/usr/bin/id -u)\";;esac\n"
        )
        end_re = re.compile(re.escape(end) + r":(-?\d+):(-?\d+)")
        end_deadline = loop.time() + timeout
        while loop.time() < end_deadline:
            if end_re.search(strip_ansi("".join(buf))):
                break
            remaining = end_deadline - loop.time()
            try:
                chunk = await asyncio.wait_for(stdout.read(65536), timeout=min(self._idle, remaining))
            except asyncio.TimeoutError:
                continue
            if chunk == "":
                raise ConnectionError("interactive SSH shell closed unexpectedly")
            buf.append(chunk)

        return self._parse("".join(buf), start, end, cmd, end_re)

    def _parse(self, output: str, start: str, end: str, cmd: str, end_re: re.Pattern) -> Tuple[str, str, int]:
        text = strip_ansi(output).replace("\r\n", "\n").replace("\r", "\n")
        text = redact_root_proof(text, self._root_proof)
        lines = text.split("\n")

        rc, start_idx, end_idx = 1, -1, -1
        for i, line in enumerate(lines):
            if start_idx == -1 and line.strip() == start:
                start_idx = i
                continue
            m = end_re.search(line)
            if m and start_idx != -1:
                rc = int(m.group(1))
                self.last_uid = int(m.group(2))
                end_idx = i
                break

        if start_idx == -1 or end_idx == -1:
            cleaned = [ln for ln in lines if start not in ln and end not in ln]
            return "\n".join(cleaned).strip(), "", rc

        body = []
        for line in lines[start_idx + 1:end_idx]:
            if start in line or end in line:
                continue
            if self._is_command_echo(line, cmd):
                continue
            body.append(line)
        return "\n".join(body).strip(), "", rc

    @staticmethod
    def _is_command_echo(line: str, cmd: str) -> bool:
        stripped = line.strip()
        if stripped == cmd:
            return True
        for prompt_char in ("$", "#", "%"):
            if prompt_char in stripped and stripped.split(prompt_char, 1)[-1].strip() == cmd:
                return True
        return False

    async def test_credential(self, username: str, password: str) -> bool:
        """Test credentials on a fresh connection without touching the persistent shell."""
        kwargs = self._connect_kwargs(username=username, password=password)
        kwargs["client_keys"] = []
        try:
            conn = await asyncssh.connect(**kwargs)
        except asyncssh.PermissionDenied:
            return False
        conn.close()
        return True

    async def close(self):
        await self._reset()
