from dataclasses import dataclass

from hackingBuddyGPT.capabilities._test_credential import TestCredentialCapability
from hackingBuddyGPT.utils.connectors.psexec import PSExecConnection
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL, is_admin_from_whoami


@dataclass
class PSExecTestCredential(TestCredentialCapability):
    conn: PSExecConnection

    def describe(self) -> str:
        return "give credentials to be tested"

    async def __call__(self, username: str, password: str) -> str:
        # Step 1: does the credential authenticate at all? A failed login/service start raises.
        try:
            test_conn = self.conn.new_with(username=username, password=password)
            test_conn.init()
        except Exception:
            return self._auth_error(username, password)

        # Step 2: the credential is valid — now find out *who* it is and whether that identity is
        # elevated, instead of assuming administrator. `whoami /groups` lists the token's group SIDs
        # (BUILTIN\Administrators = S-1-5-32-544; a filtered/non-elevated token shows it "for deny
        # only"), and NT AUTHORITY\SYSTEM shows up for the SYSTEM account.
        return self._describe_identity(test_conn, username)

    @staticmethod
    def _describe_identity(test_conn: PSExecConnection, username: str) -> str:
        try:
            groups = test_conn.run("whoami /groups")[0]
        except Exception:
            groups = ""
        if is_admin_from_whoami(groups):
            return LOGIN_AS_ROOT_SUCCESSFUL
        try:
            who = test_conn.run("whoami")[0].strip()
        except Exception:
            who = ""
        return f"Authentication successful, but user {who or username} is not an administrator\n"
