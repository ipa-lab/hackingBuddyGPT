import json

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from .common import Privesc, ThesisPrivescPrototyp
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


class ThesisLinuxPrivescPrototyp(ThesisPrivescPrototyp):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))


@use_case("Thesis Linux Privilege Escalation Prototyp")
class ThesisLinuxPrivescPrototypUseCase(AutonomousAgentUseCase[ThesisLinuxPrivescPrototyp]):
    hints: str = ""

    def init(self):
        super().init()
        if self.hints != "":
            self.agent.hint = self.read_hint()

    # simple helper that reads the hints file and returns the hint
    # for the current machine (test-case)
    def read_hint(self):
        try:
            with open(self.hints, "r") as hint_file:
                hints = json.load(hint_file)
                if self.agent.conn.hostname in hints:
                    return hints[self.agent.conn.hostname]
        except FileNotFoundError:
            self._log.console.print("[yellow]Hint file not found")
        except Exception as e:
            self._log.console.print("[yellow]Hint file could not loaded:", str(e))
        return ""
