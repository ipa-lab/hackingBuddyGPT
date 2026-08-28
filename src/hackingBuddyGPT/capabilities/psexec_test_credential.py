import warnings
from dataclasses import dataclass

from hackingBuddyGPT.utils.connectors.psexec import PSExecConnection
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL

from ..capability import Capability


@dataclass
class PSExecTestCredential(Capability):
    conn: PSExecConnection

    def describe(self) -> str:
        return "give credentials to be tested"

    def get_name(self) -> str:
        return "test_credential"

    async def __call__(self, username: str, password: str) -> str:
        try:
            test_conn = self.conn.new_with(username=username, password=password)
            test_conn.init()
            warnings.warn(
                message="full credential testing is not implemented yet for psexec, we have logged in, but do not know who we are, returning True for now",
                stacklevel=1,
            )
            return LOGIN_AS_ROOT_SUCCESSFUL
        except Exception:
            return "Authentication error, credentials are wrong\n"
