import re
from dataclasses import dataclass
from io import StringIO
from typing import override

from invoke import Responder

from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.utils.shell_root_detection import got_root

from .capability import Capability


@dataclass
class SSHRunCommand(Capability):
    conn: SSHConnection
    timeout: int = 10
    additional_description: str = ""

    @override
    def describe(self) -> str:
        desc = "Give a command to be executed in a linux shell."
        if self.conn.banner:
            desc += f"\nThe banner of the machine you're running on is:\n{self.conn.banner}"
        desc = "The environment you're in is persistent, but only for your current session."
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
        last_line = ""
        for line in out.readlines():
            if not line.startswith("[sudo] password for " + self.conn.username + ":"):
                line.replace("\r", "")
                last_line = line
                tmp = tmp + line

        # remove ansi shell codes
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        last_line = ansi_escape.sub("", last_line)

        return tmp
