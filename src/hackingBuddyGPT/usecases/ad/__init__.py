# The `AD` use-case: an autonomous LLM Active-Directory assumed-breach pentest agent, ported from
# the `cochise` research prototype. `ADUseCase` is the only registered CLI use-case; the planner,
# executor and knowledge classes are exported for direct construction (e.g. by the unit tests).
from .ad import ADPlanner, ADUseCase
from .executor import ADExecutor, PerformTaskCapability
from .knowledge import Knowledge

__all__ = ["ADUseCase", "ADPlanner", "ADExecutor", "PerformTaskCapability", "Knowledge"]
