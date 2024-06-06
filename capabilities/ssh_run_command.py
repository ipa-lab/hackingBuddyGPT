import re
from dataclasses import dataclass
from typing import Tuple

from invoke import Responder

from io import StringIO
from utils import SSHConnection
from .capability import Capability


GOT_ROOT_REXEXPs = [
    re.compile("^# $"),
    re.compile("^bash-[0-9]+.[0-9]# $")
]


@dataclass
class SSHRunCommand(Capability):
    conn: SSHConnection
    timeout: int = 10

    def describe(self) -> str:
        return f"give a command to be executed and I will respond with the terminal output when running this command over SSH on the linux machine. The given command must not require user interaction."

    def get_name(self):
        return "exec_command"

    def __call__(self, command: str) -> Tuple[str, bool]:
        got_root = False

        if command.startswith(self.get_name()):
            cmd_parts = command.split(" ", 1)
            command = cmd_parts[1]

        sudo_pass = Responder(
            pattern=r'\[sudo\] password for ' + self.conn.username + ':',
            response=self.conn.password + '\n',
        )

        out = StringIO()

        try:
            resp = self.conn.run(command, pty=True, warn=True, out_stream=out, watchers=[sudo_pass], timeout=self.timeout)
        except Exception as e:
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        last_line = ""
        for line in out.readlines():
            if not line.startswith('[sudo] password for ' + self.conn.username + ':'):
                line.replace("\r", "")
                last_line = line
                tmp = tmp + line

        # remove ansi shell codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        last_line = ansi_escape.sub('', last_line)

        for i in GOT_ROOT_REXEXPs:
            if i.fullmatch(last_line):
                got_root = True
        if last_line.startswith(f'root@{self.conn.hostname}:'):
            got_root = True
        return tmp, got_root
