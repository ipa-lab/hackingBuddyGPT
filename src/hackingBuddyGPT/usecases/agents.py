from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from mako.template import Template
from rich.panel import Panel
from typing import Dict

from hackingBuddyGPT.usecases.base import Logger
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.capabilities.capability import Capability, capabilities_to_simple_text_handler
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection


@dataclass
class Agent(ABC):
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _default_capability: Capability = None
    _log: Logger = None

    llm: OpenAIConnection = None

    def init(self):
        pass

    def before_run(self):
        pass

    def after_run(self):
        pass

    # callback
    @abstractmethod
    def perform_round(self, turn: int) -> bool:
        pass

    def add_capability(self, cap: Capability, default: bool = False):
        self._capabilities[cap.get_name()] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name: str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

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

    def init(self):
        super().init()
    
    def set_initial_state(self, initial_state:AgentWorldview):
        self._state = initial_state

    def set_template(self, template:str):
        self._template = Template(filename=template)
        self._template_size = self.llm.count_tokens(self._template.source)

    def perform_round(self, turn:int) -> bool:
        got_root : bool = False

        with self._log.console.status("[bold green]Asking LLM for a new command..."):
            # TODO output/log state
            options = self._state.to_template()
            options.update({
                'capabilities': self.get_capability_block()
            })

            # get the next command from the LLM
            answer = self.llm.get_response(self._template, **options)
            cmd = llm_util.cmd_output_fixer(answer.result)

        with self._log.console.status("[bold green]Executing that command..."):
                self._log.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                capability = self.get_capability(cmd.split(" ", 1)[0])
                result, got_root = capability(cmd)

        # log and output the command and its result
        self._log.log_db.add_log_query(self._log.run_id, turn, cmd, result, answer)
        self._state.update(capability, cmd, result)
        # TODO output/log new state
        self._log.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # if we got root, we can stop the loop
        return got_root
