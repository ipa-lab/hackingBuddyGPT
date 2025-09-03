import abc
import datetime

from dataclasses import dataclass
from mako.template import Template
from hackingBuddyGPT.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.base import UseCase
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.histories import HistoryCmdOnly, HistoryFull, HistoryNone
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection
from hackingBuddyGPT.utils.logging import log_conversation, Logger, log_param, log_section
from hackingBuddyGPT.utils.capability_manager import CapabilityManager
from typing import List


@dataclass
class CommandStrategy(UseCase, abc.ABC):

    _capabilities: CapabilityManager = None

    _template: Template = None

    _template_params = {}

    max_turns: int = 10

    llm: OpenAIConnection = None

    log: Logger = log_param

    disable_history: bool = False

    enable_compressed_history: bool = False

    def before_run(self):
        pass

    def after_command_execution(self, cmd, result, got_root):
        pass

    def get_token_overhead(self) -> int:
        return 0

    def init(self):
        super().init()

        self._capabilities = CapabilityManager(self.log)

        # TODO: make this more beautiful by just configuring a History-Instance
        if self.disable_history:
            self._history = HistoryNone()
        else:
            if self.enable_compressed_history:
                self._history = HistoryCmdOnly()
            else:
                self._history = HistoryFull()
    
    @log_conversation("Starting run...")
    def run(self, configuration):

        self.configuration = configuration
        self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

        self._template_params["capabilities"] = self._capabilities.get_capability_block()

        self.before_run()

        task_successful = False
        turn = 1
        try:
            while turn <= self.max_turns and not task_successful:
                with self.log.section(f"round {turn}"):
                    self.log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")
                    task_successful = self.perform_round(turn)
                    turn += 1
        except Exception:
            import traceback
            self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise

        # write the final result to the database and console
        if task_successful:
            self.log.run_was_success()
        else:
            self.log.run_was_failure("maximum turn number reached")
        return task_successful
    
    @log_conversation("Asking LLM for a new command(s)...")
    def perform_round(self, turn: int) -> bool:
         # get the next command and run it
        cmd, message_id = self.get_next_command()

        cmds = self.postprocess_commands(cmd)
        for cmd in cmds:
            result = self.run_command(cmd, message_id)
            # store the results in our local history
            self._history.append(cmd, result)

            task_successful = self.check_success(cmd, result)
            self.after_command_execution(cmd, result, task_successful)
            if task_successful:
                return True

        # signal if we were successful in our task
        return False

    @log_section("Asking LLM for a new command...")
    def get_next_command(self) -> tuple[str, int]:
        history = self._history.get_text_representation()

        # calculate max history size
        max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(self._template.source) - self.get_token_overhead()
        history = llm_util.trim_result_front(self.llm, max_history_size, history)

        self._template_params.update({"history": history})
        cmd = self.llm.get_response(self._template, **self._template_params)
        message_id = self.log.call_response(cmd)

        return cmd.result, message_id

    @log_section("Executing that command...")
    def run_command(self, cmd, message_id) -> str:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities._capabilities, default_capability=self._capabilities._default_capability)
        start_time = datetime.datetime.now()
        success, *output = parser(cmd)
        if not success:
            self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return output[0]

        assert len(output) == 1
        capability, cmd, result = output[0]
        duration = datetime.datetime.now() - start_time
        self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return result

    @abc.abstractmethod  
    def check_success(self, cmd:str, result:str) -> bool:
        return False

    def postprocess_commands(self, cmd:str) -> List[str]:
        return [cmd]
