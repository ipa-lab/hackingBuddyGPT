from dataclasses import dataclass
from typing import Tuple

import paramiko

from hackingBuddyGPT.utils import SSHConnection
from .capability import Capability


@dataclass
class SSHTestCredential(Capability):
    conn: SSHConnection

    def describe(self) -> str:
        return f"give credentials to be tested"

    def get_name(self):
        return "test_credential"

    def __call__(self, username: str, password: str) -> Tuple[str, bool]:
        test_conn = self.conn.new_with(username=username, password=password)
        try:
            test_conn.init()
            user = test_conn.run("whoami")[0].strip('\n\r ')
            if user == "root":
                return "Login as root was successful\n", True
            else:
                return "Authentication successful, but user is not root\n", False

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n", False
