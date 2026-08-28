import re
from dataclasses import dataclass

import paramiko
from paramiko.ssh_exception import SSHException

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL, is_root_from_id

# pull the login name out of `id` output (uid=1000(alice) ...) so the "not root" message can name it
_ID_USER = re.compile(r"\buid=\d+\(([^)]+)\)")


@dataclass
class SSHTestCredential(Capability):
    conn: SSHConnection

    def describe(self) -> str:
        return "give credentials to be tested."

    def get_name(self):
        return "test_credential"

    async def __call__(self, username: str, password: str) -> str:
        # interactive connectors expose a dedicated one-shot credential check (fresh connection,
        # id-based); use it when available and fall back to the Fabric/paramiko path otherwise.
        if hasattr(self.conn, "test_credential"):
            id_output = await self.conn.test_credential(username, password)
            if id_output is None:
                return f"Authentication error, credentials {username}:{password} are wrong\n"
            return self._describe_identity(id_output)

        test_conn = self.conn.new_with(username=username, password=password)
        try:
            for attempt in range(10):
                try:
                    test_conn.init()
                    break
                except paramiko.ssh_exception.AuthenticationException:
                    return f"Authentication error, credentials {username}:{password} are wrong\n"
                except SSHException:
                    if attempt == 9:
                        raise
                    print("Retrying SSH connection")

            return self._describe_identity(test_conn.run("id")[0])

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n"

    @staticmethod
    def _describe_identity(id_output: str) -> str:
        if is_root_from_id(id_output):
            return LOGIN_AS_ROOT_SUCCESSFUL
        match = _ID_USER.search(id_output or "")
        user = match.group(1) if match else "unknown"
        return f"Authentication successful, but user {user} is not root\n"
