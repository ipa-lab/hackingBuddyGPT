from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.capabilities.local_shell import LocalShellCapability
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.utils.local_shell import LocalShellConnection
from typing import Union
from .common import Privesc


class LinuxPrivesc(Privesc):
    conn: Union[SSHConnection, LocalShellConnection] = None
    system: str = "linux"

    def init(self):
        super().init()
        if isinstance(self.conn, LocalShellConnection):
            self.add_capability(LocalShellCapability(conn=self.conn), default=True)
            self.add_capability(SSHTestCredential(conn=self.conn))
        else:
            self.add_capability(SSHRunCommand(conn=self.conn), default=True)
            self.add_capability(SSHTestCredential(conn=self.conn))


@use_case("Linux Privilege Escalation")
class LinuxPrivescUseCase(AutonomousAgentUseCase[LinuxPrivesc]):
    pass
