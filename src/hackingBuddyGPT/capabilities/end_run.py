from dataclasses import dataclass, field
from typing import Callable, Set, override

from . import Capability


@dataclass
class EndRun(Capability):
    end_function: Callable[[], None]

    def describe(self) -> str:
        return "Ends the current run, should only be called when you think that there is no hope of success. The run will terminated automatically when all goals are achieved."

    @override
    async def __call__(self) -> str:
        self.end_function()
        return "Run has been aborted"
