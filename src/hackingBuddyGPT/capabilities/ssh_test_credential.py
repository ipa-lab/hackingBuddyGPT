from dataclasses import dataclass
from typing import Tuple

import paramiko
from paramiko.ssh_exception import SSHException
from hackingBuddyGPT.utils import SSHConnection
from .capability import Capability


@dataclass
class SSHTestCredential(Capability):
    conn: SSHConnection

    def describe(self) -> str:
        return f"give credentials to be tested. If you use this, it should be the only thing in your response to us. Do not use exec_command in the same answer to us."

    def get_name(self):
        return "test_credential"

    def __call__(self, username: str, password: str) -> Tuple[str, bool]:
        test_conn = self.conn.new_with(username=username, password=password)
        try:
            for attempt in range(3):
                try:
                    test_conn.init()
                    break;
                except paramiko.ssh_exception.AuthenticationException:
                    return "Authentication error, credentials are wrong\n", False
                except SSHException as e:
                    print("-------------------------------------------------------")
                    print(e)
                    print("Retrying")
                    print("-------------------------------------------------------")
                    if attempt == 3:
                        raise

            user = test_conn.run("whoami")[0].strip('\n\r ')
            if user == "root":
                return "Login as root was successful\n", True
            else:
                return "Authentication successful, but user is not root\n", False

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n", False
