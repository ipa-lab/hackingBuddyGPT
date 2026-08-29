import asyncio
from dataclasses import dataclass, field
from typing import Optional

import asyncssh

from hackingBuddyGPT.utils.configurable import configurable


@configurable("ssh_async", "connects to a remote host over asyncssh, one channel per command")
@dataclass
class AsyncSSHConnection:
    """Async SSH connector that runs every command in its own channel.

    Unlike the Fabric-based :class:`SSHConnection` (blocking ``.run``) and the persistent-PTY
    :class:`SSHInteractiveConnection` (a single serialised shell), this connector runs each command
    in a fresh ``asyncssh`` session over one shared connection, so several commands issued in the
    same tool-calling turn execute concurrently. It targets the "assumed breach" workflow where the
    agent drives a Kali jump host running long, independent commands (``nmap``, ``netexec``,
    ``impacket-*``, ``hashcat``). Ported from cochise's ``ssh_connection.py``.
    """

    host: str
    username: str
    password: str
    port: int = 22
    # per-command timeout in seconds; AD tooling (scans, offline cracking) is slow, so this is large
    timeout: int = 600

    _conn: Optional[asyncssh.SSHClientConnection] = field(default=None, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def init(self):
        # Connect lazily on the first run() so the asyncssh connection binds to the event loop that
        # actually drives the use-case, not the throwaway loop configurable.run_maybe_async spins up
        # during configuration resolution (same rationale as SSHInteractiveConnection).
        pass

    async def connect(self):
        self._conn = await asyncssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            known_hosts=None,  # pentest targets: do not verify host keys
        )

    async def _ensure_connected(self):
        if self._conn is not None:
            return
        async with self._lock:
            if self._conn is None:
                await self.connect()

    async def run(self, cmd: str) -> dict:
        """Run a single command, redirecting stderr into stdout, and return its result dict."""
        await self._ensure_connected()
        result = await self._conn.run(cmd, timeout=self.timeout, stderr=asyncssh.STDOUT)
        return {
            "output": result.stdout,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_status": result.returncode,
        }

    async def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None
