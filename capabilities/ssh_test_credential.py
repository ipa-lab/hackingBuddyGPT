from dataclasses import dataclass
from typing import Tuple

import paramiko

from utils import SSHConnection
from .capability import Capability


@dataclass
class SSHTestCredential(Capability):
    conn: SSHConnection

    def describe(self) -> str:
        return f"give credentials to be tested by stating `{self.get_name()} username password`"

    def get_name(self):
        return "test_credential"

    def __call__(self, command: str) -> Tuple[str, bool]:
        cmd_parts = command.split(" ")
        assert (cmd_parts[0] == self.get_name())

        if len(cmd_parts) != 3:
            return "didn't provide username/password", False

        test_conn = self.conn.new_with(username=cmd_parts[1], password=cmd_parts[2])
        try:
            test_conn.init()
            user = test_conn.run("whoami")[0].strip('\n\r ')
            if user == "root":
                return "Login as root was successful\n", True
            else:
                return "Authentication successful, but user is not root\n", False

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n", False
