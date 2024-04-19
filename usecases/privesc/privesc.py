import abc
import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict

from mako.template import Template
from rich.panel import Panel

from capabilities import Capability, SSHRunCommand, SSHTestCredential, PSExecRunCommand, PSExecTestCredential
from utils import SSHConnection, PSExecConnection, llm_util, ui
from usecases.usecase import use_case, UseCase
from usecases.usecase.roundbased import RoundBasedUseCase
from utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_state = Template(filename=str(template_dir / "update_state.txt"))

@dataclass
class Privesc(RoundBasedUseCase, UseCase, abc.ABC):

    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    hints: str = ""
    
    _sliding_history: SlidingCliHistory = None
    _state: str = ""
    _hint: str = None
    _capabilities: Dict[str, Capability] = field(default_factory=dict)

    def init(self):
        super().init()

    def setup(self):
        if self.hints != "":
            try:
                with open(self.hints, "r") as hint_file:
                    hints = json.load(hint_file)
                    if self.conn.hostname in hints:
                        self._hint = hints[self.conn.hostname]
                        self.console.print(f"[bold green]Using the following hint: '{self._hint}'")
            except:
                self.console.print("[yellow]Was not able to load hint file")
        
        if self.disable_history == False:
            self._sliding_history = SlidingCliHistory(self.llm)

    def perform_round(self, turn):
        got_root : bool = False

        with self.console.status("[bold green]Asking LLM for a new command..."):
            answer = self.get_next_command()
        cmd = answer.result

        with self.console.status("[bold green]Executing that command..."):
            if answer.result.startswith("test_credential"):
                result, got_root = self._capabilities["test_credential"](cmd)
            else:
                self.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                result, got_root = self._capabilities["run_command"](cmd)

        # log and output the command and its result
        self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)
        if self._sliding_history:
            self._sliding_history.add_command(cmd, result)
        self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # analyze the result..
        if self.enable_explanation:
            with self.console.status("[bold green]Analyze its result..."):
                answer = self.analyze_result(cmd, result)
                self.log_db.add_log_analyze_response(self._run_id, turn, cmd, answer.result, answer)

        # .. and let our local model update its state
        if self.enable_update_state:
            # this must happen before the table output as we might include the
            # status processing time in the table..
            with self.console.status("[bold green]Updating fact list.."):
                state = self.update_state(cmd, result)
                self.log_db.add_log_update_state(self._run_id, turn, "", state.result, state)

        # Output Round Data..
        self.console.print(ui.get_history_table(self.enable_explanation, self.enable_update_state, self._run_id, self.log_db, turn))

        # .. and output the updated state
        if self.enable_update_state:
            self.console.print(Panel(self._state, title="What does the LLM Know about the system?"))

        # if we got root, we can stop the loop
        return got_root

    def get_state_size(self):
        if self.enable_update_state:
            return self.llm.count_tokens(self._state)
        else:
            return 0

    def get_next_command(self):
        state_size = self.get_state_size()
        template_size = self.llm.count_tokens(template_next_cmd.source)

        history = ''
        if not self.disable_history:
            history = self._sliding_history.get_history(self.llm.context_size - llm_util.SAFETY_MARGIN - state_size - template_size)

        cmd = self.llm.get_response(template_next_cmd, _capabilities=self._capabilities, history=history, state=self._state, conn=self.conn, system=self.system, update_state=self.enable_update_state, target_user="root", hint=self._hint)
        cmd.result = llm_util.cmd_output_fixer(cmd.result)
        return cmd

    def analyze_result(self, cmd, result):
        state_size = self.get_state_size()
        target_size = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size

        # ugly, but cut down result to fit context size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        return self.llm.get_response(template_analyze, cmd=cmd, resp=result, facts=self._state)

    def update_state(self, cmd, result):
        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        ctx = self.llm.context_size
        state_size = self.get_state_size()
        target_size = ctx - llm_util.SAFETY_MARGIN - state_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_state, cmd=cmd, resp=result, facts=self._state)
        self._state = result.result
        return result

@use_case("linux_privesc", "Linux Privilege Escalation")
@dataclass
class LinuxPrivesc(Privesc):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self._capabilities["run_command"] = SSHRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = SSHTestCredential(conn=self.conn)


@use_case("windows_privesc", "Windows Privilege Escalation")
@dataclass
class WindowsPrivesc(Privesc):
    conn: PSExecConnection = None
    system: str = "Windows"

    def init(self):
        super().init()
        self._capabilities["run_command"] = PSExecRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = PSExecTestCredential(conn=self.conn)
