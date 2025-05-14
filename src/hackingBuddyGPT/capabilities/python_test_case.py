
from hackingBuddyGPT.capabilities import Capability


from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

@dataclass
class PythonTestCase(Capability):
    description: str
    input: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    registry: List[Tuple[str, dict, dict]] = field(default_factory=list)

    def describe(self) -> str:
        """
        Returns a description of the test case.
        """
        return f"Test Case: {self.description}\nInput: {self.input}\nExpected Output: {self.expected_output}"
    def __call__(self, description: str, input: dict, expected_output: dict) -> dict:
        self.registry.append((description, input, expected_output))
        return {"description": description, "input": input, "expected_output": expected_output}
