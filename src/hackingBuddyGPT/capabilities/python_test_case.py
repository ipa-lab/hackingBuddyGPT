from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from hackingBuddyGPT.capabilities import Capability


@dataclass
class PythonTestCase(Capability):
    description: str
    input: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    registry: List[Tuple[str, str]] = field(default_factory=list)

    def describe(self) -> str:
        """
        Returns a description of the test case.
        """
        return f"Test Case: {self.description}\nInput: {self.input}\nExpected Output: {self.expected_output}"
    def __call__(self, title: str, content: str) -> str:
        self.registry.append((title, content))
        return f" Test Case:\n{title}: {content}"
