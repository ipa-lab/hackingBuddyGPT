from dataclasses import dataclass, field
from typing import Dict

from capabilities.capability import Capability
from usecases.common_patterns import RoundBasedUseCase


@dataclass
class Agent(RoundBasedUseCase):

    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _default_capability: Capability = None

    def init(self):
        super().init()

    def add_capability(self, cap:Capability, default:bool=False):
        self._capabilities[cap.get_name()] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name:str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

    def get_capability_block(self) -> str:
        return "You can either\n\n" + "\n".join(map(lambda i: f"- {i.describe()}", self._capabilities.values()))
