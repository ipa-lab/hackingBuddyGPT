from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import SSHConnection

from .common import Privesc


class LinuxPrivesc(Privesc):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))


@use_case("Linux Privilege Escalation")
class LinuxPrivescUseCase(AutonomousAgentUseCase[LinuxPrivesc]):
    pass
