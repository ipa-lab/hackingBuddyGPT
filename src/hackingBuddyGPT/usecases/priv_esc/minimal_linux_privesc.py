from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from ._base import TemplatedCommandPrivEsc
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection


@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(TemplatedCommandPrivEsc):
    conn: SSHInteractiveConnection = None
    system = "Linux"
    target_user = "root"
    goal_details = " in a persistent shell or authenticate as that user"

    def _add_capabilities(self):
        self._capabilities.add_capability(SSHInteractiveRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

    def check_success(self, cmd: str, result: str) -> bool:
        return self.conn.root_verified
