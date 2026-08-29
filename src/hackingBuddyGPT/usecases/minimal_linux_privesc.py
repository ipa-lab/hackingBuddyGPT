from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases._privesc_common import TemplatedCommandPrivEsc
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection
from hackingBuddyGPT.utils.shell_root_detection import check_command_success


@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(TemplatedCommandPrivEsc):
    conn: SSHInteractiveConnection = None
    system = "Linux"
    target_user = "root"

    def _add_capabilities(self):
        self._capabilities.add_capability(SSHInteractiveRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

    def check_success(self, cmd: str, result: str) -> bool:
        return check_command_success(self.conn.hostname, cmd, result, uid=self.conn.last_uid)
