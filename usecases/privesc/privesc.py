import abc
import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict

from mako.template import Template
from rich.panel import Panel

from capabilities import Capability, SSHRunCommand, SSHTestCredential, PSExecRunCommand, PSExecTestCredential
from utils.openai.openai_llm import OpenAIConnection
from utils import SSHConnection, Console, DbStorage, PSExecConnection, llm_util, ui
from usecases.usecase import use_case, UseCase

template_dir = pathlib.Path(__file__).parent / "templates"


@dataclass
class Privesc(UseCase, abc.ABC):
    log_db: DbStorage
    console: Console
    system: str
    llm: OpenAIConnection = None
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    max_turns: int = 10
    tag: str = ""
    hints: str = ""

    _state: str = ""
    _run_id: int = 0
    _hint: str = None
    _capabilities: Dict[str, Capability] = field(default_factory=dict)

    def init(self):
        super().init()

        self._run_id = self.log_db.create_new_run(self.llm.model, self.llm.context_size, self.tag)

        if self.hints != "":
            try:
                with open(self.hints, "r") as hint_file:
                    hints = json.load(hint_file)
                    if self.conn.hostname in hints:
                        self._hint = hints[self.conn.hostname]
                        self.console.print(f"[bold green]Using the following hint: '{self._hint}'")
            except:
                self.console.print("[yellow]Was not able to load hint file")

    def run(self):
        turn = 1
        got_root = False
        while turn <= self.max_turns and not got_root:
            self.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")
            with self.console.status("[bold green]Asking LLM for a new command..."):
                answer = self.get_next_command()
            cmd = answer.result

            with self.console.status("[bold green]Executing that command..."):
                if answer.result.startswith("test_credential"):
                    result, got_root = self._capabilities["test_credential"](cmd)
                else:
                    self.console.print(Panel(answer.result, title=f"[bold cyan]Got command from LLM:"))
                    result, got_root = self._capabilities["run_command"](cmd)

            self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)

            # output the command and its result
            self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

            # analyze the result..
            if self.enable_explanation:
                with self.console.status("[bold green]Analyze its result..."):
                    answer = self.analyze_result(cmd, result)
                    self.log_db.add_log_analyze_response(self._run_id, turn, cmd, answer.result, answer)

            # .. and let our local model representation update its state
            if self.enable_update_state:
                # this must happen before the table output as we might include the
                # status processing time in the table..
                with self.console.status("[bold green]Updating fact list.."):
                    state = self.update_state(cmd, result)
                    self.log_db.add_log_update_state(self._run_id, turn, "", state.result, state)

            # Output Round Data
            self.console.print(ui.get_history_table(self.enable_explanation, self.enable_update_state, self._run_id, self.log_db, turn))

            if self.enable_update_state:
                self.console.print(Panel(self._state, title="What does the LLM Know about the system?"))

            # finish turn and commit logs to storage
            self.log_db.commit()
            turn += 1

        # write the final result to the database and console
        if got_root:
            self.log_db.run_was_success(self._run_id, turn)
            self.console.print(Panel("[bold green]Got Root!", title="Run finished"))
        else:
            self.log_db.run_was_failure(self._run_id, turn)
            self.console.print(Panel("[green]maximum turn number reached", title="Run finished"))

    def get_state_size(self):
        if self.enable_update_state:
            return self.llm.count_tokens(self._state)
        else:
            return 0

    def get_next_command(self):
        state_size = self.get_state_size()
        template_size = self.llm.count_tokens(self.get_next_command_template().source)

        history = ''
        if not self.disable_history:
            result: str = ""
            for itm in self.log_db.get_cmd_history(self._run_id):
                result += f"$ {itm[0]}\n{itm[1]}"

            # trim it down if too large
            allowed = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size - template_size
            history = llm_util.trim_result_front(self.llm, allowed, result)

        cmd = self.llm.get_response(self.get_next_command_template(), _capabilities=self._capabilities, history=history, state=self._state, conn=self.conn, system=self.system, update_state=self.enable_update_state, target_user="root", hint=self._hint)
        cmd.result = llm_util.cmd_output_fixer(cmd.result)
        return cmd

    def analyze_result(self, cmd, result):
        state_size = self.get_state_size()
        target_size = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size

        # ugly, but cut down result to fit context size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        return self.llm.get_response(self.get_analyze_template(), cmd=cmd, resp=result, facts=self._state)

    def update_state(self, cmd, result):
        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        ctx = self.llm.context_size
        state_size = self.get_state_size()
        target_size = ctx - llm_util.SAFETY_MARGIN - state_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(self.get_update_state_template(), cmd=cmd, resp=result, facts=self._state)
        self._state = result.result
        return result


    def get_next_command_template(self):
        return Template(filename=str(template_dir / "query_next_command.txt"))

    def get_analyze_template(self):
        return Template(filename=str(template_dir / "analyze_cmd.txt"))

    def get_update_state_template(self):
        return Template(filename=str(template_dir / "update_state.txt"))


@use_case("linux_privesc", "Linux Privilege Escalation")
@dataclass
class LinuxPrivesc(Privesc):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self._capabilities["run_command"] = SSHRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = SSHTestCredential(conn=self.conn)


@use_case("windows privesc", "Windows Privilege Escalation")
@dataclass
class WindowsPrivesc(Privesc):
    conn: PSExecConnection = None
    system: str = "Windows"

    def init(self):
        super().init()
        self._capabilities["run_command"] = PSExecRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = PSExecTestCredential(conn=self.conn)
