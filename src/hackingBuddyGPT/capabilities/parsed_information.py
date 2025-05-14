from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from hackingBuddyGPT.capabilities import Capability


from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

@dataclass
class ParsedInformation(Capability):
    status_code: str
    reason_phrase:  Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)
    response_body: Dict[str, Any] = field(default_factory=dict)
    registry: List[Tuple[str, str, str, str]] = field(default_factory=list)

    def describe(self) -> str:
        """
        Returns a description of the test case.
        """
        return f"Parsed information for {self.status_code}, reason_phrase: {self.reason_phrase}, headers: {self.headers}, response_body: {self.response_body} "
    def __call__(self, status_code: str, reason_phrase: str, headers: str, response_body:str) -> dict:
        self.registry.append((status_code, response_body, headers,response_body))

        return {"status_code": status_code, "reason_phrase": reason_phrase, "headers": headers, "response_body": response_body}
