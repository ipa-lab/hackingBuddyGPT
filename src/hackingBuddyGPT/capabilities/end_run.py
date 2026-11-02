from dataclasses import dataclass, field
from typing import Callable, Set, override

from hackingBuddyGPT.capability import Capability


@dataclass
class EndRun(Capability):
    end_function: Callable[[], None]

    def describe(self) -> str:
        return (
            "Ends the current run, should only be called when you think that there is no hope of success. "
            "The run will terminated automatically when all goals are achieved. "
            "You MUST fill the `summary` argument of this same call with the full structured closing report: "
            "the MITRE ATT&CK techniques in the order you used them, the observed impact of each step, and the "
            "controls that blocked your actions."
        )

    @override
    async def __call__(self, summary: str) -> str:
        # `summary` is captured in the tool-call trace (arguments + result) before the run is
        # cancelled, so the final structured report is recoverable alongside the termination event.
        self.end_function()
        return f"Run has been aborted. Final report recorded:\n{summary}"
