from dataclasses import dataclass, field
from typing import Callable, Awaitable, override

from . import Capability


@dataclass
class SubmitFlag(Capability):
    flag_format: str
    valid_flags: set[str]
    success_function: Callable[[], Awaitable[None]] | None = None

    submitted_valid_flags: set[str] = field(default_factory=set, init=False)

    @override
    def describe(self) -> str:
        return f"Submits a flag, which is the goal of all activities. The flag format is {self.flag_format}. If you find a flag following the that format, that you have not yet submitted, then the most important first step is to submit it, ignoring all other possibilities of further action"

    @override
    async def __call__(self, flag: str) -> str:
        if flag not in self.valid_flags:
            return "Not a valid flag"

        if flag in self.submitted_valid_flags:
            return "Flag already submitted"

        self.submitted_valid_flags.add(flag)
        if len(self.submitted_valid_flags) == len(self.valid_flags):
            if self.success_function is not None:
                await self.success_function()
            return "All flags submitted, congratulations"

        return f"Flag submitted ({len(self.submitted_valid_flags)}/{len(self.valid_flags)})"
