import json

from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.privesc.linux import LinuxPrivesc


@use_case("Linux Privilege Escalation using hints from a hint file initial guidance")
class ExPrivEscLinuxHintFileUseCase(AutonomousAgentUseCase[LinuxPrivesc]):
    hints: str = None

    def init(self):
        super().init()
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
            self.log.console.print("[yellow]Hint file not found")
        except Exception as e:
            self.log.console.print("[yellow]Hint file could not loaded:", str(e))
        return ""
