from dataclasses import dataclass
from capabilities.psexec_run_command import PSExecRunCommand
from capabilities.psexec_test_credential import PSExecTestCredential
from usecases.base import use_case
from usecases.privesc.common import Privesc
from utils.psexec.psexec import PSExecConnection


@use_case("windows_privesc", "Windows Privilege Escalation")
@dataclass
class WindowsPrivesc(Privesc):
    conn: PSExecConnection = None
    system: str = "Windows"

    def init(self):
        super().init()
        self._capabilities["run_command"] = PSExecRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = PSExecTestCredential(conn=self.conn)