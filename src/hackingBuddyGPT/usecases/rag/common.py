import datetime
import pathlib
import re

from dataclasses import dataclass, field
from mako.template import Template
from typing import Any, Dict, Optional

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.utils.logging import log_section, log_conversation
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_chain_of_thought = Template(filename=str(template_dir / "chain_of_thought.txt"))


@dataclass
class ThesisPrivescPrototype(Agent):
    system: str = ""
    enable_explanation: bool = False
    enable_update_state: bool = False
    enable_compressed_history: bool = False
    disable_history: bool = False
    enable_chain_of_thought: bool = False
    hint: str = ""

    _sliding_history: SlidingCliHistory = None
    _state: str = ""
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _template_params: Dict[str, Any] = field(default_factory=dict)
    _max_history_size: int = 0

    def before_run(self):
        if self.hint != "":
            self.log.status_message(f"[bold green]Using the following hint: '{self.hint}'")

        if self.disable_history is False:
            self._sliding_history = SlidingCliHistory(self.llm)

        self._template_params = {
            "capabilities": self.get_capability_block(),
            "system": self.system,
            "hint": self.hint,
            "conn": self.conn,
            "update_state": self.enable_update_state,
            "target_user": "root",
            'chain_of_thought': self.enable_chain_of_thought
        }

        if self.enable_chain_of_thought:
            self._chain_of_thought = template_chain_of_thought.source

        template_size = self.llm.count_tokens(template_next_cmd.source)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - template_size

    def perform_round(self, turn: int) -> bool:
        # get the next command and run it
        cmd, message_id = self.get_next_command()


        if self.enable_chain_of_thought:
            # command = re.findall("<command>(.*?)</command>", answer.result)
            command = re.findall(r"<command>([\s\S]*?)</command>", cmd)

            if len(command) > 0:
                command = "\n".join(command)
                cmd = command

        # split if there are multiple commands
        commands = self.split_into_multiple_commands(cmd)

        cmds, result, got_root = self.run_command(commands, message_id)


        # log and output the command and its result
        if self._sliding_history:
            if self.enable_compressed_history:
                self._sliding_history.add_command_only(cmd, result)
            else:
                self._sliding_history.add_command(cmd, result)

        # analyze the result..
        if self.enable_explanation:
            self.analyze_result(cmd, result)

        # Output Round Data..  # TODO: reimplement
        # self.log.console.print(ui.get_history_table(self.enable_explanation, self.enable_update_state, self.log.run_id, self.log.log_db, turn))

        # if we got root, we can stop the loop
        return got_root

    def get_chain_of_thought_size(self) -> int:
        if self.enable_chain_of_thought:
            return self.llm.count_tokens(self._chain_of_thought)
        else:
            return 0

    @log_conversation("Asking LLM for a new command...", start_section=True)
    def get_next_command(self) -> tuple[str, int]:
        history = ""
        if not self.disable_history:
            if self.enable_compressed_history:
                history = self._sliding_history.get_commands_and_last_output(self._max_history_size - self.get_chain_of_thought_size())
            else:
                history = self._sliding_history.get_history(self._max_history_size - self.get_chain_of_thought_size())

        self._template_params.update({"history": history, 'CoT': self._chain_of_thought})

        cmd = self.llm.get_response(template_next_cmd, **self._template_params)
        message_id = self.log.call_response(cmd)

        # return llm_util.cmd_output_fixer(cmd.result), message_id
        return cmd.result, message_id

    @log_section("Executing that command...")
    def run_command(self, cmd, message_id) -> tuple[Optional[str], Optional[str], bool]:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities, default_capability=self._default_capability)

        cmds = ""
        result = ""
        got_root = False
        for i, command in enumerate(cmd):
            start_time = datetime.datetime.now()
            success, *output = parser(command)
            if not success:
                self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=command, result_text=output[0], duration=0)
                return cmds, output[0], False
            assert len(output) == 1
            capability, cmd_, (result_, got_root_) = output[0]
            cmds += cmd_ + "\n"
            result += result_ + "\n"
            got_root = got_root or got_root_
            duration = datetime.datetime.now() - start_time
            self.log.add_tool_call(message_id, tool_call_id=i, function_name=capability, arguments=cmd_,
                                   result_text=result_, duration=duration)

        cmds = cmds.rstrip()
        result = result.rstrip()
        return cmds, result, got_root

    @log_conversation("Analyze its result...", start_section=True)
    def analyze_result(self, cmd, result):
        state_size = self.get_state_size()
        target_size = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size

        # ugly, but cut down result to fit context size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        answer = self.llm.get_response(template_analyze, cmd=cmd, resp=result, facts=self._state)
        self.log.call_response(answer)

    def split_into_multiple_commands(self, response: str):
        ret = self.split_with_delimiters(response, ["test_credential", "exec_command"])

        # strip trailing newlines
        ret = [r.rstrip() for r in ret]

        # remove first entry. For some reason its always empty
        if len(ret) > 1:
            ret = ret[1:]

        # combine keywords with their corresponding input
        if len(ret) > 1:
            ret = [ret[i] + ret[i + 1] for i in range(0, len(ret) - 1, 2)]
        return ret

    def split_with_delimiters(self, input: str, delimiters):
        # Create a regex pattern to match any of the delimiters
        regex_pattern = f"({'|'.join(map(re.escape, delimiters))})"
        # Use re.split to split the text while keeping the delimiters
        return re.split(regex_pattern, input)