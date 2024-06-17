from dataclasses import dataclass, field
from typing import  Set, Callable

from . import Capability


@dataclass
class SubmitHTTPMethod(Capability):
    http_methods_format: str
    valid_http_methods: Set[str]
    success_function: Callable[[], None] = None

    submitted_valid_http_methods: Set[str] = field(default_factory=set, init=False)

    def describe(self) -> str:
        return f"Submits a HTTP methods, which is the goal of all activities. The HTTP methods format is {self.http_methods_format}. If you find a flag following the that format, that you have not yet submitted, then the most important first step is to submit it, ignoring all other possibilities of further action"

    def __call__(self, flag: str) -> str:
        if flag not in self.valid_http_methods:
            return "Not a valid HTTP method"

        if flag in self.submitted_valid_http_methods:
            return "HTTP Method already submitted"

        self.submitted_valid_http_methods.add(flag)
        if len(self.submitted_valid_http_methods) == len(self.valid_http_methods):
            if self.success_function is not None:
                self.success_function()
            else:
                return "All HTTP methods submitted, congratulations"

        return f"HTTP Methods submitted ({len(self.submitted_valid_http_methods)}/{len(self.valid_http_methods)})"
