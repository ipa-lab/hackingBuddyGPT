import abc
from dataclasses import dataclass
import datetime
from typing import List, Optional
import re

from mako.template import Template

from hackingBuddyGPT.capabilities.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.base import UseCase
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection
from hackingBuddyGPT.utils.logging import log_conversation, Logger, log_param, log_section
from hackingBuddyGPT.utils.capability_manager import CapabilityManager
from hackingBuddyGPT.utils.shell_root_detection import got_root

@dataclass
class CommandStrategy(UseCase, abc.ABC):

    _capabilities: CapabilityManager = None

    _sliding_history: SlidingCliHistory = None

    _max_history_size: int = 0

    _template: Template = None

    _template_params = {}

    max_turns: int = 10

    llm: OpenAIConnection = None

    log: Logger = log_param

    disable_history: bool = False

    enable_compressed_history: bool = False

    def before_run(self):
        pass

    def after_run(self):
        pass

    def after_round(self, cmd, result, got_root):
        pass

    def get_space_for_history(self):
        pass

    def init(self):
        super().init()

        self._capabilities = CapabilityManager(self.log)

        self._sliding_history = SlidingCliHistory(self.llm)

    @log_section("Asking LLM for a new command...")
    def get_next_command(self) -> tuple[str, int]:
        history = ""
        if not self.disable_history:
            if self.enable_compressed_history:
                history = self._sliding_history.get_commands_and_last_output(self._max_history_size - self.get_state_size())
            else:
                history = self._sliding_history.get_history(self._max_history_size - self.get_state_size())

        self._template_params.update({"history": history})
        cmd = self.llm.get_response(self._template, **self._template_params)
        message_id = self.log.call_response(cmd)

        return cmd.result, message_id

    @log_section("Executing that command...")
    def run_command(self, cmd, message_id) -> tuple[Optional[str], bool]:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities._capabilities, default_capability=self._capabilities._default_capability)
        start_time = datetime.datetime.now()
        success, *output = parser(cmd)
        if not success:
            self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return output[0], False

        assert len(output) == 1
        capability, cmd, (result, got_root) = output[0]
        duration = datetime.datetime.now() - start_time
        self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return result, got_root
    
    def check_success(self, cmd, result) -> bool:
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        last_line = result.split("\n")[-1] if result else ""
        last_line = ansi_escape.sub("", last_line)
        return got_root(self.conn.hostname, last_line)

    def postprocess_commands(self, cmd:str) -> List[str]:
        return [cmd]

    @log_conversation("Asking LLM for a new command...")
    def perform_round(self, turn: int) -> bool:
         # get the next command and run it
        cmd, message_id = self.get_next_command()

        cmds = self.postprocess_commands(cmd)
        for cmd in cmds:
            result, task_successful = self.run_command(cmd, message_id)

        # maybe move the 'got root' detection here?
        # TODO: also can I use llm-as-judge for that? or do I have to do this
        #       on a per-action base (maybe add a .task_successful(cmd, result, options) -> boolean to the action?
        task_successful2 = self.check_success(cmd, result)
        assert(task_successful == task_successful2)

        self.after_round(cmd, result, task_successful)

        # store the results in our local history
        if not self.disable_history:
            if self.enable_compressed_history:
                self._sliding_history.add_command_only(cmds, result)
            else:
                self._sliding_history.add_command(cmds, result)

        # signal if we were successful in our task
        return task_successful

    @log_conversation("Starting run...")
    def run(self, configuration):

        self.configuration = configuration
        self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

        self._template_params["capabilities"] = self._capabilities.get_capability_block()


        # calculate sizes
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(self._template.source)

        self.before_run()

        got_root = False

        turn = 1
        try:
            while turn <= self.max_turns and not got_root:
                with self.log.section(f"round {turn}"):
                    self.log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

                    got_root = self.perform_round(turn)

                    turn += 1

            self.after_run()

            # write the final result to the database and console
            if got_root:
                self.log.run_was_success()
            else:
                self.log.run_was_failure("maximum turn number reached")

            return got_root
        except Exception:
            import traceback
            self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise