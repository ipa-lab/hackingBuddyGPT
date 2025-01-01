import os
import pathlib
import re
from dataclasses import dataclass, field

from langchain_core.vectorstores import VectorStoreRetriever
from mako.template import Template
from rich.panel import Panel
from typing import Any, Dict
from transformers import Qwen2Tokenizer

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.utils import llm_util, ui
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory
from hackingBuddyGPT.utils.rag_utility import initiate_rag

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_state = Template(filename=str(template_dir / "update_state.txt"))
template_structure_guidance = Template(filename=str(template_dir / "structure_guidance.txt"))
template_chain_of_thought = Template(filename=str(template_dir / "chain_of_thought.txt"))
template_rag = Template(filename=str(template_dir / "rag_prompt.txt"))
template_rag_alt = Template(filename=str(template_dir / "rag_alt_prompt.txt"))

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

            # TODO remove and ask andreas how to fix this problem
            cmd = cmd.replace("exec_command", "")

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

@dataclass
class ThesisPrivescPrototyp(Agent):

    system: str = ''
    enable_analysis: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    enable_compressed_history:bool = False
    hint: str = ""
    disable_duplicates: bool = False
    enable_structure_guidance: bool = False
    enable_chain_of_thought: bool = False
    enable_rag: bool = False
    enable_alt_rag: bool = False

    _sliding_history: SlidingCliHistory = None
    _state: str = ""
    _analyze: str = ""
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _template_params: Dict[str, Any] = field(default_factory=dict)
    _max_history_size: int = 0
    _previously_used_commands: [str] = field(default_factory=list)
    _structure_guidance: str = ""
    _chain_of_thought: str = ""
    _rag_text: str = ""
    _rag_document_retriever: VectorStoreRetriever = None
    _rag_alt_text: str = ""

    def init(self):
        super().init()

    def before_run(self):
        if self.hint != "":
            self._log.console.print(f"[bold green]Using the following hint: '{self.hint}'")

        if self.disable_history is False:
            self._sliding_history = SlidingCliHistory(self.llm)

        if self.enable_rag or self.enable_alt_rag:
            self._rag_document_retriever = initiate_rag()


        if "Qwen2.5" in self.llm.model:
            print("Set up Qwen Tokenizer")
            self.llm.qwen_tokenizer = Qwen2Tokenizer.from_pretrained("Qwen/Qwen-tokenizer")


        self._template_params = {
            'capabilities': self.get_capability_block(),
            'system': self.system,
            'hint': self.hint,
            'conn': self.conn,
            'update_state': self.enable_update_state,
            'target_user': 'root',
            'structure_guidance': self.enable_structure_guidance,
            'chain_of_thought': self.enable_chain_of_thought,
            'alt_rag_enabled': self.enable_alt_rag
        }

        if self.enable_structure_guidance:
            self._structure_guidance = template_structure_guidance.source

        if self.enable_chain_of_thought:
            self._chain_of_thought = template_chain_of_thought.source

        template_size = self.llm.count_tokens(template_next_cmd.source)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - template_size

    def perform_round(self, turn: int) -> bool:
        got_root: bool = False

        with self._log.console.status("[bold green]Asking LLM for a new command..."):
            answer = self.get_next_command()
        cmd = answer.result

        if self.enable_chain_of_thought:
            # command = re.findall("<command>(.*?)</command>", answer.result)
            command = re.findall(r"<command>([\s\S]*?)</command>", answer.result)

            if len(command) > 0:
                command = "\n".join(command)
                cmd = command
            # if len(command) > 0:
            #     cmd = command[0]

        # split if there are multiple commands
        commands = self.split_into_multiple_commands(cmd)

        with self._log.console.status("[bold green]Executing that command..."):
            self._log.console.print(Panel(cmd, title="[bold cyan]Got command from LLM:"))
            _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities, default_capability=self._default_capability)

            output_list = []
            for c in commands:
                success, *output = parser(c)
                if not success:
                    self._log.console.print(Panel(output[0], title="[bold red]Error parsing command:"))
                    return False
                output_list.append(output)
            cmd = ""
            result = ""
            got_root = False
            for o in output_list:
                assert (len(output) == 1)
                capability, cmd_, (result_, got_root_) = o[0]
                cmd += cmd_ + "\n"
                result += result_ + "\n"
                got_root = got_root or got_root_
            cmd = cmd.rstrip()
            result = result.rstrip()

            # TODO remove and ask andreas how to fix this problem
            # cmd = cmd.replace("exec_command", "")

        # log and output the command and its result
        self._log.log_db.add_log_query(self._log.run_id, turn, cmd, result, answer)
        if self._sliding_history:
            if self.enable_compressed_history:
                self._sliding_history.add_command_only(cmd, result)
            else:
                self._sliding_history.add_command(cmd, result)

        self._log.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # alternative RAG
        if self.enable_alt_rag:
            with self._log.console.status("[bold green]Retrieving relevant documents from Vectorstore..."):
                query = self.get_alt_rag_query(cmd, result)
                relevant_documents = self._rag_document_retriever.invoke(query.result)
                relevant_information = "".join([d.page_content + "\n" for d in relevant_documents])
                self._rag_alt_text = llm_util.trim_result_front(self.llm, 1200, relevant_information)
                self._log.log_db.add_log_rag_response(self._log.run_id, turn, cmd, query.result, query)

        # retrieving additional information
        if self.enable_rag:
            with self._log.console.status("[bold green]Retrieving relevant documents from Vectorstore..."):
                query = self.get_rag_query(cmd, result)
                relevant_documents = self._rag_document_retriever.invoke(query.result)
                relevant_information = "".join([d.page_content + "\n" for d in relevant_documents])
                self._rag_text = llm_util.trim_result_front(self.llm, int(os.environ['rag_return_token_limit']), relevant_information)
                self._log.log_db.add_log_rag_response(self._log.run_id, turn, cmd, query.result, query)

        # analyze the result..
        if self.enable_analysis:
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
        self._log.console.print(ui.get_history_table(self.enable_analysis, self.enable_update_state, self._log.run_id, self._log.log_db, turn, self.enable_rag or self.enable_alt_rag))

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

    def get_analyze_size(self) -> int:
        if self.enable_analysis:
            return self.llm.count_tokens(self._analyze)
        else:
            return 0

    def get_structure_guidance_size(self) -> int:
        if self.enable_structure_guidance:
            return self.llm.count_tokens(self._structure_guidance)
        else:
            return 0

    def get_chain_of_thought_size(self) -> int:
        if self.enable_chain_of_thought:
            return self.llm.count_tokens(self._chain_of_thought)
        else:
            return 0

    def get_rag_size(self) -> int:
        if self.enable_rag:
            return self.llm.count_tokens(self._rag_text)
        else:
            return 0

    def get_alt_rag_size(self) -> int:
        if self.enable_alt_rag:
            return self.llm.count_tokens(self._rag_alt_text)
        else:
            return 0

    def get_next_command(self) -> llm_util.LLMResult:
        history = ''
        if not self.disable_history:
            if self.enable_compressed_history:
                history = self._sliding_history.get_commands_and_last_output(self._max_history_size - self.get_state_size() - self.get_analyze_size() - self.get_structure_guidance_size() - self.get_chain_of_thought_size() - self.get_alt_rag_size())
            else:
                history = self._sliding_history.get_history(self._max_history_size - self.get_state_size() - self.get_analyze_size() - self.get_structure_guidance_size() - self.get_chain_of_thought_size() - self.get_alt_rag_size())
        self._template_params.update({
            'history': history,
            'state': self._state,
            'analyze': self._analyze,
            'guidance': self._structure_guidance,
            'CoT': self._chain_of_thought,
            'alt_rag_text': self._rag_alt_text
        })

        cmd = self.llm.get_response(template_next_cmd, **self._template_params)
        # cmd.result = llm_util.cmd_output_fixer(cmd.result)

        if self.disable_duplicates:
            count = 0
            while cmd.result in self._previously_used_commands:
                count += 1
                self._log.console.print(f"Repeated command: '{cmd.result}', fetching new command")
                cmd = self.llm.get_response(template_next_cmd, **self._template_params)
                cmd.result = llm_util.cmd_output_fixer(cmd.result)
                if count == 25:
                    break
        self._previously_used_commands.append(cmd.result)
        return cmd

    def analyze_result(self, cmd, result):
        ctx = self.llm.context_size

        template_size = self.llm.count_tokens(template_analyze.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size - self.get_rag_size()
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_analyze, cmd=cmd, resp=result, rag_enabled=self.enable_rag, rag_text=self._rag_text, hint=self.hint)
        self._analyze = result.result
        return result

    def get_rag_query(self, cmd, result):
        ctx = self.llm.context_size
        template_size = self.llm.count_tokens(template_rag.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_rag, cmd=cmd, resp=result)
        return result
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

    def get_alt_rag_query(self, cmd, result):
        ctx = self.llm.context_size
        template_size = self.llm.count_tokens(template_rag_alt.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_rag, cmd=cmd, resp=result)
        return result


