from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import use_case, AutonomousAgentUseCase


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
