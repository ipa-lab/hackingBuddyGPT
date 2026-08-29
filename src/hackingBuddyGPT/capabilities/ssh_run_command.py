from dataclasses import dataclass
from io import StringIO
from typing import override

from invoke import Responder

from hackingBuddyGPT.capabilities._ssh_command import SSHCommandCapability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection


@dataclass
class SSHRunCommand(SSHCommandCapability):
    conn: SSHConnection

    _intro = (
        "Give a command to be executed in a linux shell. Each command runs in its own shell, so "
        "state is not preserved between commands."
    )

    @override
    async def __call__(self, command: str) -> str:
        command = self._strip_command_prefix(command)

        sudo_pass = Responder(
            pattern=r"\[sudo\] password for " + self.conn.username + ":",
            response=self.conn.password + "\n",
        )

        out = StringIO()

        try:
            self.conn.run(command, pty=True, warn=True, out_stream=out, watchers=[sudo_pass], timeout=self.timeout)
        except Exception:
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        for line in out.readlines():
            if not line.startswith("[sudo] password for " + self.conn.username + ":"):
                line = line.replace("\r", "")
                tmp = tmp + line

        return tmp
