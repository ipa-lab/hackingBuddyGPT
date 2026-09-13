from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection

from ._base import TemplatedCommandPrivEsc
from ._linux_capabilities import LinuxPrivEscRunCommand, LinuxPrivEscTestCredential


@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(TemplatedCommandPrivEsc):
    conn: SSHInteractiveConnection = None
    system = "Linux"
    target_user = "root"
    goal_details = " in the persistent shell or authenticate as that user with 'test_credential'"

    def _add_capabilities(self):
        self._run_command = LinuxPrivEscRunCommand(conn=self.conn)
        self._test_credential = LinuxPrivEscTestCredential(conn=self.conn)
        self._capabilities.add_capability(self._run_command, default=True)
        self._capabilities.add_capability(self._test_credential)

    def check_success(self, cmd: str, result: str) -> bool:
        return self._run_command.root_verified or self._test_credential.root_verified
