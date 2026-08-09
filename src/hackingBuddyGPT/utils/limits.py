import datetime
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, override

from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.llm_util import LLMResult

# we would want to add bound=SupportsDunderGT[Any] here, but we don't use typeshed for anything else, so I didn't want to add in an additional dependency
GTT = TypeVar("GTT")


def parent_limited(child_limit: GTT | None, parent_limit: GTT | None) -> GTT | None:
    if child_limit is None:
        return parent_limit
    if parent_limit is None:
        return child_limit

    return min(child_limit, parent_limit)


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

    _parent: "Limits | None" = None
    _rounds: int = 0
    _tokens: int = 0
    _cost: float = 0.0
    _start_time: datetime.datetime | None = None
    _max_duration: datetime.timedelta | None = None

    _state: RunState = RunState.RUNNING
    _reason: str | None = None

    def __post_init__(self):
        self._max_duration = datetime.timedelta(seconds=self.max_duration)

    def start(self):
        if self._parent:
            self._parent.start()

        if self._start_time is None:
            self._start_time = datetime.datetime.now()

    def reached(self) -> bool:
        if self._parent and self._parent.reached():
            if self._parent.reason:
                self._reason = f"Parent limit reached: {self._parent.reason}"
            else:
                self._reason = "Parent completed"
            return True

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

    def round_str(self) -> str:
        if self._parent:
            return f"{self._parent.round_str()} < {self._rounds}/{self.max_rounds}"
        return f"{self._rounds}/{self.max_rounds}"

    def register_round(self):
        if self._parent:
            self._parent.register_round()

        self._rounds += 1

    @property
    def rounds(self) -> int:
        return self._rounds

    def rounds_remaining(self) -> int | None:
        return parent_limited(
            child_limit=self.max_rounds - self._rounds if self.max_rounds else None,
            parent_limit=self._parent.rounds_remaining() if self._parent else None,
        )

    def register_message(self, message: LLMResult):
        if self._parent:
            self._parent.register_message(message)

        self._tokens += message.total_tokens
        self._cost += message.cost

    @property
    def tokens(self) -> int:
        return self._tokens

    def tokens_remaining(self) -> int | None:
        return parent_limited(
            child_limit=self.max_tokens - self._tokens if self.max_tokens else None,
            parent_limit=self._parent.tokens_remaining() if self._parent else None,
        )

    @property
    def cost(self) -> float:
        return self._cost

    def cost_remaining(self) -> float | None:
        return parent_limited(
            child_limit=self.max_cost - self._cost if self.max_cost else None,
            parent_limit=self._parent.cost_remaining() if self._parent else None,
        )

    @property
    def duration(self) -> datetime.timedelta | None:
        if not self._start_time:
            return None
        return datetime.datetime.now() - self._start_time

    def time_remaining(self) -> datetime.timedelta | None:
        child_limit: datetime.timedelta | None = None
        if self._max_duration and self._start_time:
            child_limit = self._max_duration - (datetime.datetime.now() - self._start_time)

        return parent_limited(
            child_limit=child_limit,
            parent_limit=self._parent.time_remaining() if self._parent else None,
        )

    def cancel(self):
        self._state = RunState.CANCELLED
        self._reason = "Cancelled"

    def complete(self):
        self._state = RunState.COMPLETED

    @property
    def reason(self):
        return self._reason

    def sub_limit(self, max_rounds: int, max_tokens: int, max_cost: float, max_duration: int) -> "Limits":
        if (remaining_rounds := self.rounds_remaining()) is not None and max_rounds > remaining_rounds:
            raise ValueError("Could not create sub limit: max_rounds exceeds remaining parent rounds")
        if (remaining_tokens := self.tokens_remaining()) is not None and max_tokens > remaining_tokens:
            raise ValueError("Could not create sub limit: max_tokens exceeds remaining parent tokens")
        if (remaining_cost := self.cost_remaining()) is not None and max_cost > remaining_cost:
            raise ValueError("Could not create sub limit: max_cost exceeds remaining parent cost")
        if (remaining_time := self.time_remaining()) is not None and datetime.timedelta(
            seconds=max_duration
        ) > remaining_time:
            raise ValueError("Could not create sub limit: max_duration exceeds remaining parent time")

        return self.__class__(
            max_rounds=max_rounds, max_tokens=max_tokens, max_cost=max_cost, max_duration=max_duration, _parent=self
        )

    def sub_limit_from(self, other: "Limits") -> "Limits":
        return self.sub_limit(
            max_rounds=other.max_rounds,
            max_tokens=other.max_tokens,
            max_cost=other.max_cost,
            max_duration=other.max_duration,
        )

    @override
    def __str__(self) -> str:
        res: list[str] = []
        if (remaining_rounds := self.rounds_remaining()) is not None:
            res.append(f"remaining_rounds={remaining_rounds}")
        if (remaining_tokens := self.tokens_remaining()) is not None:
            res.append(f"remaining_tokens={remaining_tokens}")
        if (remaining_cost := self.cost_remaining()) is not None:
            res.append(f"remaining_cost={remaining_cost}")
        if (remaining_time := self.time_remaining()) is not None:
            res.append(f"remaining_duration={remaining_time}")
        return ", ".join(res)
