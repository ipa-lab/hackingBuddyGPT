from dataclasses import dataclass, field
from typing import Callable, Set

from . import Capability


@dataclass
class SubmitFlag(Capability):
    flag_format: str
    valid_flags: Set[str]
    success_function: Callable[[], None] = None

    submitted_valid_flags: Set[str] = field(default_factory=set, init=False)

    def describe(self) -> str:
        return f"Submits a flag, which is the goal of all activities. The flag format is {self.flag_format}. If you find a flag following the that format, that you have not yet submitted, then the most important first step is to submit it, ignoring all other possibilities of further action"

    def __call__(self, flag: str) -> str:
        if flag not in self.valid_flags:
            return "Not a valid flag"

        if flag in self.submitted_valid_flags:
            return "Flag already submitted"

        self.submitted_valid_flags.add(flag)
        if len(self.submitted_valid_flags) == len(self.valid_flags):
            if self.success_function is not None:
                self.success_function()
            else:
                return "All flags submitted, congratulations"

        return f"Flag submitted ({len(self.submitted_valid_flags)}/{len(self.valid_flags)})"
