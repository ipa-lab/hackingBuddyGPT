from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection

from ._base import TemplatedCommandPrivEsc


@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(TemplatedCommandPrivEsc):
    conn: SSHInteractiveConnection = None
    system = "Linux"
    target_user = "root"
    goal_details = " in the persistent shell or authenticate as that user with 'test_credential'"

    def _add_capabilities(self):
        self._capabilities.add_capability(SSHInteractiveRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

    def check_success(self, cmd: str, result: str) -> bool:
        return self.conn.root_verified
