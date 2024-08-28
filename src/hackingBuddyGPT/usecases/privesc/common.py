import pathlib
from dataclasses import dataclass, field
from mako.template import Template
from rich.panel import Panel
from typing import Any, Dict

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.utils import llm_util, ui
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_state = Template(filename=str(template_dir / "update_state.txt"))


@dataclass
class Privesc(Agent):

    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    hint: str = ""

    _sliding_history: SlidingCliHistory = None
    _state: str = ""
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _template_params: Dict[str, Any] = field(default_factory=dict)
    _max_history_size: int = 0

    def init(self):
        super().init()

    def before_run(self):
        if self.hint != "":
            self._log.console.print(f"[bold green]Using the following hint: '{self.hint}'")

        if self.disable_history is False:
            self._sliding_history = SlidingCliHistory(self.llm)

        self._template_params = {
            'capabilities': self.get_capability_block(),
            'system': self.system,
            'hint': self.hint,
            'conn': self.conn,
            'update_state': self.enable_update_state,
            'target_user': 'root'
        }

        template_size = self.llm.count_tokens(template_next_cmd.source)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - template_size

    def perform_round(self, turn: int) -> bool:
        got_root: bool = False

        with self._log.console.status("[bold green]Asking LLM for a new command..."):
            answer = self.get_next_command()
        cmd = answer.result

        with self._log.console.status("[bold green]Executing that command..."):
            self._log.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
            _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities, default_capability=self._default_capability)
            success, *output = parser(cmd)
            if not success:
                self._log.console.print(Panel(output[0], title="[bold red]Error parsing command:"))
                return False

            assert(len(output) == 1)
            capability, cmd, (result, got_root) = output[0]

        # log and output the command and its result
        self._log.log_db.add_log_query(self._log.run_id, turn, cmd, result, answer)
        if self._sliding_history:
            self._sliding_history.add_command(cmd, result)

        self._log.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # analyze the result..
        if self.enable_explanation:
            with self._log.console.status("[bold green]Analyze its result..."):
                answer = self.analyze_result(cmd, result)
                self._log.log_db.add_log_analyze_response(self._log.run_id, turn, cmd, answer.result, answer)

        # .. and let our local model update its state
        if self.enable_update_state:
            # this must happen before the table output as we might include the
            # status processing time in the table..
            with self._log.console.status("[bold green]Updating fact list.."):
                state = self.update_state(cmd, result)
                self._log.log_db.add_log_update_state(self._log.run_id, turn, "", state.result, state)

        # Output Round Data..
        self._log.console.print(ui.get_history_table(self.enable_explanation, self.enable_update_state, self._log.run_id, self._log.log_db, turn))

        # .. and output the updated state
        if self.enable_update_state:
            self._log.console.print(Panel(self._state, title="What does the LLM Know about the system?"))

        # if we got root, we can stop the loop
        return got_root

    def get_state_size(self) -> int:
        if self.enable_update_state:
            return self.llm.count_tokens(self._state)
        else:
            return 0

    def get_next_command(self) -> llm_util.LLMResult:
        history = ''
        if not self.disable_history:
            history = self._sliding_history.get_history(self._max_history_size - self.get_state_size())

        self._template_params.update({
            'history': history,
            'state': self._state
        })

        cmd = self.llm.get_response(template_next_cmd, **self._template_params)
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
