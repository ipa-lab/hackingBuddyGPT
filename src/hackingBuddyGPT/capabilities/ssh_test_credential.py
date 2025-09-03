import paramiko

from dataclasses import dataclass
from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection
from paramiko.ssh_exception import SSHException

@dataclass
class SSHTestCredential(Capability):
    conn: SSHConnection

    def describe(self) -> str:
        return "give credentials to be tested."

    def get_name(self):
        return "test_credential"

    def __call__(self, username: str, password: str) -> str:
        test_conn = self.conn.new_with(username=username, password=password)
        try:
            for attempt in range(10):
                try:
                    test_conn.init()
                    break;
                except paramiko.ssh_exception.AuthenticationException:
                    return f"Authentication error, credentials {username}:{password} are wrong\n"
                except SSHException as e:
                    if attempt == 9:
                        raise
                    print("-------------------------------------------------------")
                    print(e)
                    print("Retrying")
                    print("-------------------------------------------------------")


            user = test_conn.run("whoami")[0].strip("\n\r ")
            if user == "root":
                return f"Login as root was successful\n"
            else:
                return f"Authentication successful, but user {user} is not root\n"

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n"
