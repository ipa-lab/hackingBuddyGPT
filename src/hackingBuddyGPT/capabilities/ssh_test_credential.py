from dataclasses import dataclass

import paramiko
from paramiko.ssh_exception import SSHException

from hackingBuddyGPT.capabilities._test_credential import TestCredentialCapability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL


@dataclass
class SSHTestCredential(TestCredentialCapability):
    conn: SSHConnection

    def describe(self) -> str:
        return "give credentials to be tested."

    async def __call__(self, username: str, password: str) -> str:
        # Interactive connectors test credentials on a fresh connection.
        self.conn.root_verified = False
        if hasattr(self.conn, "test_credential"):
            authenticated = await self.conn.test_credential(username, password)
        else:
            authenticated = False
            test_conn = self.conn.new_with(username=username, password=password)
            test_conn.keyfilename = ""
            for attempt in range(10):
                try:
                    test_conn.init()
                    authenticated = True
                    break
                except paramiko.ssh_exception.AuthenticationException:
                    break
                except SSHException:
                    if attempt == 9:
                        raise
                    print("Retrying SSH connection")

        if not authenticated:
            return self._auth_error(username, password)
        self.conn.root_verified = username == "root"
        if self.conn.root_verified:
            return LOGIN_AS_ROOT_SUCCESSFUL
        return f"Authentication successful, but user {username} is not root\n"
