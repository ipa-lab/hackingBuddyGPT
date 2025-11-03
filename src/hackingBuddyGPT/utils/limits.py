from dataclasses import dataclass
from enum import Enum


@dataclass
class Limits:
    class RunState(Enum):
        RUNNING = 0
        COMPLETED = 1
        CANCELLED = 2

    rounds: int = 0
    max_rounds: int | None = None
    tokens: int = 0
    max_tokens: int | None = None
    cancelled: RunState = RunState.RUNNING

    def reached(self) -> bool:
        if self.max_rounds is not None and self.rounds >= self.max_rounds:
            return True

        if self.max_tokens is not None and self.tokens >= self.max_tokens:
            return True

        return self.cancelled != self.RunState.RUNNING

    def reason(self) -> str | None:
        if self.max_rounds is not None and self.rounds >= self.max_rounds:
            return f"Reached maximum rounds ({self.max_rounds})"

        if self.max_tokens is not None and self.tokens >= self.max_tokens:
            return f"Reached maximum tokens ({self.max_tokens})"

        if self.cancelled == self.RunState.CANCELLED:
            return "Cancelled"

        return None

    def register_round(self):
        self.rounds += 1

    def cancel(self):
        self.cancelled = self.RunState.CANCELLED

    def complete(self):
        self.cancelled = self.RunState.COMPLETED
