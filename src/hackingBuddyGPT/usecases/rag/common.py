import datetime
import pathlib
import re
import os

from dataclasses import dataclass, field
from mako.template import Template
from typing import Any, Dict, Optional
from langchain_core.vectorstores import VectorStoreRetriever

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.utils import rag as rag_util
from hackingBuddyGPT.utils.logging import log_section, log_conversation
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_chain_of_thought = Template(filename=str(template_dir / "chain_of_thought.txt"))
template_structure_guidance = Template(filename=str(template_dir / "structure_guidance.txt"))
template_rag = Template(filename=str(template_dir / "rag_prompt.txt"))


@dataclass
class ThesisPrivescPrototype(Agent):
    system: str = ""
    enable_analysis: bool = False
    enable_update_state: bool = False
    enable_compressed_history: bool = False
    disable_history: bool = False
    enable_chain_of_thought: bool = False
    enable_structure_guidance: bool = False
    enable_rag: bool = False
    _rag_document_retriever: VectorStoreRetriever = None
    hint: str = ""

    _sliding_history: SlidingCliHistory = None
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _template_params: Dict[str, Any] = field(default_factory=dict)
    _max_history_size: int = 0
    _analyze: str = ""
    _structure_guidance: str = ""
    _chain_of_thought: str = ""
    _rag_text: str = ""

    def before_run(self):
        if self.hint != "":
            self.log.status_message(f"[bold green]Using the following hint: '{self.hint}'")

        if self.disable_history is False:
            self._sliding_history = SlidingCliHistory(self.llm)

        if self.enable_rag:
            self._rag_document_retriever = rag_util.initiate_rag()

        self._template_params = {
            "capabilities": self.get_capability_block(),
            "system": self.system,
            "hint": self.hint,
            "conn": self.conn,
            "target_user": "root",
            'structure_guidance': self.enable_structure_guidance,
            'chain_of_thought': self.enable_chain_of_thought
        }

        if self.enable_structure_guidance:
            self._structure_guidance = template_structure_guidance.source

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
                self._sliding_history.add_command_only(cmds, result)
            else:
                self._sliding_history.add_command(cmds, result)

        if self.enable_rag:
            query = self.get_rag_query(cmds, result)
            relevant_documents = self._rag_document_retriever.invoke(query.result)
            relevant_information = "".join([d.page_content + "\n" for d in relevant_documents])
            self._rag_text = llm_util.trim_result_front(self.llm, int(os.environ['rag_return_token_limit']),
                                                        relevant_information)

        # analyze the result..
        if self.enable_analysis:
            self.analyze_result(cmds, result)


        # if we got root, we can stop the loop
        return got_root

    def get_chain_of_thought_size(self) -> int:
        if self.enable_chain_of_thought:
            return self.llm.count_tokens(self._chain_of_thought)
        else:
            return 0

    def get_structure_guidance_size(self) -> int:
        if self.enable_structure_guidance:
            return self.llm.count_tokens(self._structure_guidance)
        else:
            return 0

    def get_analyze_size(self) -> int:
        if self.enable_analysis:
            return self.llm.count_tokens(self._analyze)
        else:
            return 0

    def get_rag_size(self) -> int:
        if self.enable_rag:
            return self.llm.count_tokens(self._rag_text)
        else:
            return 0

    @log_conversation("Asking LLM for a new command...", start_section=True)
    def get_next_command(self) -> tuple[str, int]:
        history = ""
        if not self.disable_history:
            if self.enable_compressed_history:
                history = self._sliding_history.get_commands_and_last_output(self._max_history_size - self.get_chain_of_thought_size() - self.get_structure_guidance_size() - self.get_analyze_size())
            else:
                history = self._sliding_history.get_history(self._max_history_size - self.get_chain_of_thought_size() - self.get_structure_guidance_size() - self.get_analyze_size())

        self._template_params.update({
            "history": history,
            'CoT': self._chain_of_thought,
            'analyze': self._analyze,
            'guidance': self._structure_guidance
        })

        cmd = self.llm.get_response(template_next_cmd, **self._template_params)
        message_id = self.log.call_response(cmd)

        # return llm_util.cmd_output_fixer(cmd.result), message_id
        return cmd.result, message_id


    @log_conversation("Asking LLM for a search query...", start_section=True)
    def get_rag_query(self, cmd, result):
        ctx = self.llm.context_size
        template_size = self.llm.count_tokens(template_rag.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_rag, cmd=cmd, resp=result)
        self.log.call_response(result)
        return result

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
        ctx = self.llm.context_size

        template_size = self.llm.count_tokens(template_analyze.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size - self.get_rag_size()
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_analyze, cmd=cmd, resp=result, rag_enabled=self.enable_rag, rag_text=self._rag_text, hint=self.hint)
        self._analyze = result.result
        self.log.call_response(result)

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