import abc
import datetime

from dataclasses import dataclass
from mako.template import Template
from hackingBuddyGPT.capability import capabilities_to_simple_text_handler
from hackingBuddyGPT.usecases.usecase import AutonomousUseCase, UseCase
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.histories import HistoryCmdOnly, HistoryFull, HistoryNone
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.llm import LiteLLM
from hackingBuddyGPT.utils.logging import log_conversation, Logger, log_param, log_section
from hackingBuddyGPT.utils.capability_manager import CapabilityManager
from typing import List


@dataclass
class CommandStrategy(AutonomousUseCase, abc.ABC):
    """Simple-text command strategy: templates the whole history into one prompt each round and
    parses a bare command out of the reply. Runs on the shared ``AutonomousUseCase.run`` loop
    (Limits-driven) like every other use-case; ``max_turns`` is folded into the round limit in
    ``init``, and success is signalled through ``limits.complete()`` when ``check_success`` holds."""

    _capabilities: CapabilityManager = None

    _template: Template = None

    _template_params = {}

    max_turns: int = 10

    llm: LiteLLM = None

    log: Logger = log_param

    disable_history: bool = False

    enable_compressed_history: bool = False

    async def before_run(self):
        # The shared loop calls this once before the first round; expose the capability list to the
        # template here (it used to be set at the top of the old bespoke run()).
        self._template_params["capabilities"] = self._capabilities.get_capability_block()

    async def after_command_execution(self, cmd, result, got_root):
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

        # Bound the run with Limits like every other use-case. max_turns is this strategy's round
        # budget, so fold it into the round cap (strictest of it and any injected --max_rounds wins);
        # the injected cost/token/duration caps apply on top. A never-reached default keeps the class
        # usable when built directly (e.g. in tests) with no Limits injected.
        if self.limits is None:
            self.limits = Limits(max_rounds=0, max_tokens=0, max_cost=0, max_duration=0)
        self.limits.max_rounds = min(self.max_turns, self.limits.max_rounds or self.max_turns)

    @log_conversation("Asking LLM for a new command(s)...")
    async def perform_round(self):
        # get the next command and run it
        cmd, message_id = await self.get_next_command()

        cmds = self.postprocess_commands(cmd)
        for cmd in cmds:
            result = await self.run_command(cmd, message_id)
            # store the results in our local history
            self._history.append(cmd, result)

            task_successful = self.check_success(cmd, result)
            await self.after_command_execution(cmd, result, task_successful)
            if task_successful:
                # Mark the run solved; the shared loop's limits.reached() then ends it as a success.
                self.limits.complete()
                break

        self.limits.register_round()

    @log_section("Asking LLM for a new command...")
    async def get_next_command(self) -> tuple[str, int]:
        history = self._history.get_text_representation()

        # calculate max history size
        max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(self._template.source) - self.get_token_overhead()
        history = llm_util.trim_result_front(self.llm, max_history_size, history)

        self._template_params.update({"history": history})
        cmd = self.llm.get_response(self._template, **self._template_params)
        message_id = await self.log.call_response(cmd)
        # Account this round's LLM call against the run limits so the cost/token caps apply to strategy
        # use-cases too (duration is tracked by the loop; rounds by register_round in perform_round).
        self.limits.register_message(cmd)

        return cmd.result, message_id

    @log_section("Executing that command...")
    async def run_command(self, cmd, message_id) -> str:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities._capabilities, default_capability=self._capabilities._default_capability)
        start_time = datetime.datetime.now()
        success, *output = parser(cmd)
        if not success:
            await self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return output[0]

        assert len(output) == 1
        capability, cmd, result = output[0]
        # capability execution is asynchronous now, the simple-text handler returns the coroutine
        result = await result
        duration = datetime.datetime.now() - start_time
        await self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return result

    @abc.abstractmethod
    def check_success(self, cmd:str, result:str) -> bool:
        return False

    def postprocess_commands(self, cmd:str) -> List[str]:
        return [cmd]

@dataclass
class SimpleStrategy(UseCase, abc.ABC):
    max_turns: int = 10

    llm: LiteLLM = None

    log: Logger = log_param

    _capabilities: CapabilityManager = None

    def init(self):
        super().init()
        self._capabilities = CapabilityManager(self.log)

    @abc.abstractmethod
    async def perform_round(self, turn: int):
        pass

    async def before_run(self):
        pass

    async def after_run(self):
        pass

    async def run(self, configuration):
        # SimpleStrategy subclasses are phase engines driven by an orchestrator (e.g. WebAPITesting
        # calls their perform_round(turn) directly and owns the round/limits loop). None is run via
        # this method: WebAPITesting overrides run(); the engines are stepped externally. The concrete
        # stub keeps subclasses instantiable while making the contract explicit.
        raise NotImplementedError(
            "SimpleStrategy subclasses are driven by their orchestrator; call perform_round() directly."
        )
