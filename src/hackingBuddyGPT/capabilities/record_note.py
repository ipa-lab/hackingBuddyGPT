from dataclasses import dataclass, field
from typing import List, Tuple

from . import Capability


@dataclass
class RecordNote(Capability):
    registry: List[Tuple[str, str]] = field(default_factory=list)

    def describe(self) -> str:
        return "Records a note, which is useful for keeping track of information that you may need later."

    def __call__(self, title: str, content: str) -> str:
        self.registry.append((title, content))
        return f"note recorded\n{title}: {content}"
