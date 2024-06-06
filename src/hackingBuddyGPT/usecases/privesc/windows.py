from dataclasses import dataclass

from hackingBuddyGPT.capabilities.psexec_run_command import PSExecRunCommand
from hackingBuddyGPT.capabilities.psexec_test_credential import PSExecTestCredential
from hackingBuddyGPT.usecases.base import use_case
from hackingBuddyGPT.usecases.privesc.common import Privesc
from hackingBuddyGPT.utils.psexec.psexec import PSExecConnection


@use_case("windows_privesc", "Windows Privilege Escalation")
@dataclass
class WindowsPrivesc(Privesc):
    conn: PSExecConnection = None
    system: str = "Windows"

    def init(self):
        super().init()
        self.add_capability(PSExecRunCommand(conn=self.conn), default=True)
        self.add_capability(PSExecTestCredential(conn=self.conn))