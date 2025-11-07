import datetime
from dataclasses import dataclass
from enum import Enum

from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.llm_util import LLMResult


class RunState(Enum):
    RUNNING = 0
    COMPLETED = 1
    CANCELLED = 2


@dataclass
class Limits:
    max_rounds: int = parameter(desc="Maximum number of rounds (0 is no limit)", default=100)
    max_tokens: int = parameter(desc="Maximum number of tokens (input+output+thinking, 0 is no limit)", default=0)
    max_cost: float = parameter(desc="Maximum cost in dollars (0 is no limit)", default=10.0)
    max_duration: int = parameter(desc="Maximum duration of the run in seconds (0 is no limit)", default=0)

    _rounds: int = 0
    _tokens: int = 0
    _cost: float = 0.0
    _start_time: datetime.datetime | None = None
    _max_duration: datetime.timedelta | None = None

    _state: RunState = RunState.RUNNING
    _reason: str | None = None

    def __post_init__(self):
        if self.max_duration is not None:
            self._max_duration = datetime.timedelta(seconds=self.max_duration)

    def start(self):
        self._start_time = datetime.datetime.now()

    def reached(self) -> bool:
        if self._reason is not None:
            return True

        if self.max_rounds and self._rounds >= self.max_rounds:
            self._reason = f"Reached maximum rounds ({self.max_rounds})"
            return True

        if self.max_tokens and self._tokens >= self.max_tokens:
            self._reason = f"Reached maximum tokens ({self.max_tokens})"
            return True

        if self.max_cost and self._cost >= self.max_cost:
            self._reason = f"Reached maximum cost ({self.max_cost})"
            return True

        if self._max_duration and self._start_time is not None:
            duration = datetime.datetime.now() - self._start_time
            if duration >= self._max_duration:
                self._reason = f"Reached maximum duration ({self._max_duration})"
                return True

        return self._state != RunState.RUNNING

    def register_round(self):
        self._rounds += 1

    def rounds_remaining(self):
        if self.max_rounds is None:
            return None
        return self.max_rounds - self._rounds

    def register_message(self, message: LLMResult):
        self._tokens += message.total_tokens
        self._cost += message.cost

    def tokens_remaining(self) -> int | None:
        if self.max_tokens is None:
            return None
        return self.max_tokens - self._tokens

    def cost_remaining(self) -> float | None:
        if self.max_cost is None:
            return None
        return self.max_cost - self._cost

    def time_remaining(self) -> datetime.timedelta | None:
        if not self._max_duration or self._start_time is None:
            return None
        return self._max_duration - (datetime.datetime.now() - self._start_time)

    def cancel(self):
        self._state = RunState.CANCELLED
        self._reason = "Cancelled"

    def complete(self):
        self._state = RunState.COMPLETED

    @property
    def reason(self):
        return self._reason
