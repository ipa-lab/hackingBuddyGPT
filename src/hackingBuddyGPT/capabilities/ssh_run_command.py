from dataclasses import dataclass
from io import StringIO
from invoke import Responder
from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection

@dataclass
class SSHRunCommand(Capability):
    conn: SSHConnection
    timeout: int = 10

    def describe(self) -> str:
        return "give a command to be executed and I will respond with the terminal output when running this command over SSH on the linux machine. The given command must not require user interaction. Do not use quotation marks in front and after your command."

    def get_name(self):
        return "exec_command"

    def __call__(self, command: str) -> str:
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
                line.replace("\r", "")
                tmp = tmp + line

        return tmp
