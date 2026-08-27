from dataclasses import dataclass
from io import StringIO
from typing import override

from invoke import Responder

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection


@dataclass
class SSHRunCommand(Capability):
    conn: SSHConnection
    timeout: int = 10
    additional_description: str = ""

    @override
    def describe(self) -> str:
        desc = (
            "Give a command to be executed in a linux shell. Each command runs in its own shell, so "
            "state is not preserved between commands."
        )
        if self.conn.banner:
            desc += f"\nThe banner of the machine you're running on is:\n{self.conn.banner}"
        return desc + self.additional_description

    @override
    def get_name(self):
        return "execute_bash_command"

    @override
    async def __call__(self, command: str) -> str:
        if command.startswith(self.get_name()):
            cmd_parts = command.split(" ", 1)
            if len(cmd_parts) == 1:
                command = ""
            else:
                command = cmd_parts[1]

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
