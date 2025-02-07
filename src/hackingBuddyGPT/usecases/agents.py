import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from mako.template import Template
from typing import Dict

from hackingBuddyGPT.utils.logging import log_conversation, GlobalLogger
from hackingBuddyGPT.capabilities.capability import (
    Capability,
    capabilities_to_simple_text_handler,
)
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection


@dataclass
class Agent(ABC):
    log: GlobalLogger = None

    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _default_capability: Capability = None

    llm: OpenAIConnection = None

    async def init(self):  # noqa: B027
        pass

    async def before_run(self):  # noqa: B027
        pass

    async def after_run(self):  # noqa: B027
        pass

    # callback
    @abstractmethod
    async def perform_round(self, turn: int) -> bool:
        pass

    def add_capability(self, cap: Capability, name: str = None, default: bool = False):
        if name is None:
            name = cap.get_name()
        self._capabilities[name] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name: str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

    async def run_capability_json(self, message_id: int, tool_call_id: str, capability_name: str, arguments: str) -> str:
        capability = self.get_capability(capability_name)

        tic = datetime.datetime.now()
        try:
            result = await capability.to_model().model_validate_json(arguments).execute()
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        await self.log.add_tool_call(message_id, tool_call_id, capability_name, arguments, result, duration)
        return result

    def get_capability_block(self) -> str:
        capability_descriptions, _parser = capabilities_to_simple_text_handler(self._capabilities)
        return "You can either\n\n" + "\n".join(f"- {description}" for description in capability_descriptions.values())


@dataclass
class AgentWorldview(ABC):
    @abstractmethod
    def to_template(self):
        pass

    @abstractmethod
    def update(self, capability, cmd, result):
        pass


class TemplatedAgent(Agent):
    _state: AgentWorldview = None
    _template: Template = None
    _template_size: int = 0

    async def init(self):
        await super().init()

    def set_initial_state(self, initial_state: AgentWorldview):
        self._state = initial_state

    def set_template(self, template: str):
        self._template = Template(filename=template)
        self._template_size = self.llm.count_tokens(self._template.source)

    @log_conversation("Asking LLM for a new command...")
    async def perform_round(self, turn: int) -> bool:
        # get the next command from the LLM
        answer = self.llm.get_response(self._template, capabilities=self.get_capability_block(), **self._state.to_template())
        message_id = self.log.call_response(answer)

        capability, cmd, result, got_root = self.run_capability_simple_text(message_id, llm_util.cmd_output_fixer(answer.result))

        self._state.update(capability, cmd, result)

        # if we got root, we can stop the loop
        return got_root
