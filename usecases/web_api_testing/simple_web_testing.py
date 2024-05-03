import pathlib
from dataclasses import dataclass, field
from typing import Dict

from mako.template import Template
from rich.panel import Panel

from capabilities import Capability, SSHRunCommand, SSHTestCredential
from usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from utils import SSHConnection, llm_util
from usecases.usecase import use_case
from usecases.usecase.roundbased import RoundBasedUseCase
from utils.cli_history import SlidingCliHistory


@use_case("simple_web_api_testing",  "Minimal implementation of a web api testing use case")
@dataclass
class SimpleWebAPITesting(RoundBasedUseCase):
    conn: SSHConnection = None

    _prompt_history: SlidingCliHistory = None
    _capabilities: Dict[str, Capability] = field(default_factory=dict)

    def init(self):
        super().init()
        self._prompt_history = SlidingCliHistory(self.llm)
        self._capabilities["run_command"] = SSHRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = SSHTestCredential(conn=self.conn)
        self.prompt_engineer = PromptEngineer(strategy=PromptStrategy.CHAIN_OF_THOUGHT, api_key=self.llm.api_key, history=self._prompt_history)
    def perform_round(self, turn):
        got_root: bool = False

        with self.console.status("[bold green]Asking LLM for a new command..."):
            # get as much history as fits into the target context size
            history = self._prompt_history.get_history(
                self.llm.context_size - llm_util.SAFETY_MARGIN - self._template_size)

            # Create prompt
            prompt = self.prompt_engineer.generate_prompt()

            # get the next command from the LLM
            answer = self.llm.get_response(prompt, _capabilities=self._capabilities, history=history,
                                           conn=self.conn)
            cmd = llm_util.cmd_output_fixer(answer.result)

        with self.console.status("[bold green]Executing that command..."):
            if answer.result.startswith("test_credential"):
                result, got_root = self._capabilities["test_credential"](cmd)
            else:
                self.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                result, got_root = self._capabilities["run_command"](cmd)

        # log and output the command and its result
        self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)
        self._prompt_history.add_command(cmd, result)
        self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # if we got root, we can stop the loop
        return got_root