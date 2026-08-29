from hackingBuddyGPT.capabilities import PSExecRunCommand, PSExecTestCredential
from hackingBuddyGPT.usecases._privesc_common import TemplatedCommandPrivEsc
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.psexec import PSExecConnection
from hackingBuddyGPT.utils.shell_root_detection import check_windows_admin_success


@use_case("Strategy-based Windows Priv-Escalation")
class PrivEscWindows(TemplatedCommandPrivEsc):
    conn: PSExecConnection = None
    system = "Windows"
    target_user = "Administrator"

    def _add_capabilities(self):
        self._capabilities.add_capability(PSExecRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(PSExecTestCredential(conn=self.conn))

    def check_success(self, cmd: str, result: str) -> bool:
        return check_windows_admin_success(cmd, result)
