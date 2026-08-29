import pathlib
from typing import override

from hackingBuddyGPT.capabilities.ssh_execute_command import SSHExecuteCommand
from hackingBuddyGPT.capability import function_call_capability
from hackingBuddyGPT.usecases.ad.executor import PerformTaskCapability, add_knowledge_capabilities
from hackingBuddyGPT.usecases.ad.knowledge import Knowledge
from hackingBuddyGPT.usecases.agents import ChatAgent
from hackingBuddyGPT.usecases.usecase import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.connectors.async_ssh_connection import AsyncSSHConnection
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.llm import LiteLLM

TEMPLATE_DIR = pathlib.Path(__file__).parent / "templates"
DEFAULT_SCENARIO_PATH = str(TEMPLATE_DIR / "scenario.md")
PLANNER_STRUCTURE = (TEMPLATE_DIR / "planner_structure.md").read_text()
PLANNER_PROMPT = (TEMPLATE_DIR / "planner_prompt.md").read_text()

# the two fixed user turns used both for the initial plan and for history compaction
PLAN_STRUCTURE_TASK = (
    PLANNER_STRUCTURE
    + "\n\n# Task\n\nProvide the hierarchical task plan as answer. Do not include a title or an appendix."
)
INITIAL_PLAN_INSTRUCTION = (
    "Create me an initial plan to achieve the overall objective. Break down the overall objective "
    "into smaller tasks and subtasks. Do not include generic steps, only very specific ones that are "
    "directly relevant for achieving the overall objective. Be concise."
)


class ADPlanner(ChatAgent):
    """Persistent strategic agent (ported from cochise's Planner).

    It maintains a tree-structured task plan and, each round, delegates exactly one task to a fresh
    worker via the ``perform_task`` tool; it also maintains a shared :class:`Knowledge` base and can
    end the run early via ``objective_complete``. Its chat history is optionally compacted (plan
    regenerated, history reset) to keep long assumed-breach runs within the context window.
    """

    llm: LiteLLM

    conn: AsyncSSHConnection = None
    scenario_path: str = parameter(
        desc="path to the scenario / system-prompt markdown file (the objective, target scope and rules)",
        default=DEFAULT_SCENARIO_PATH,
    )
    executor_max_rounds: int = parameter(
        desc="maximum number of rounds a delegated worker (executor) may run", default=25
    )
    compaction_max_interactions: int = parameter(
        desc="compact the planner history after this many rounds (0 = disabled)", default=0
    )
    compaction_max_context_tokens: int = parameter(
        desc="compact the planner history once its token count reaches this (0 = disabled)", default=0
    )

    def _create_plan(self, messages, limits: Limits) -> str:
        """One tool-less LLM call that returns a task-plan text; cost is charged to ``limits``."""
        result = self.llm.get_response(messages)
        limits.register_message(result)
        return result.answer

    @override
    async def before_run(self, limits: Limits):
        self.scenario = pathlib.Path(self.scenario_path).read_text()
        self.knowledge = Knowledge()
        self._interaction_counter = 0

        # the worker's SSH tool; the same lazily-connected AsyncSSHConnection is shared across workers
        ssh_capability = SSHExecuteCommand(conn=self.conn)

        # planner tools: knowledge mutators (on the global knowledge), perform_task and objective_complete
        add_knowledge_capabilities(self, self.knowledge)
        self.add_capability(
            PerformTaskCapability(
                llm=self.llm,
                log=self.log,
                parent_limits=limits,
                ssh_capability=ssh_capability,
                knowledge=self.knowledge,
                scenario=self.scenario,
                max_rounds=self.executor_max_rounds,
            )
        )

        async def objective_complete(evidence: str) -> str:
            """Declare the overall objective achieved; ends the run and records it as a success."""
            limits.complete()
            return f"Objective marked complete (evidence: {evidence}). The run will now end."

        self.add_capability(
            function_call_capability(
                objective_complete,
                "Signal that the overall objective (e.g. domain dominance / compromising the domain "
                "administrator) has been achieved. Call this ONLY with concrete supporting evidence; "
                "it ends the run and records it as a success.",
                name="objective_complete",
            )
        )

        # seed the persistent history: scenario + plan-structure as system, an initial plan, then the
        # 'select next task' prompt, so the history always ends on the task-selection turn.
        self._system = self.scenario + "\n\n# Task Plan Creation and Evolution\n\n" + PLANNER_STRUCTURE
        await self.log.system_message(self._system)
        plan = self._create_plan(
            [
                {"role": "system", "content": self.scenario},
                {"role": "user", "content": PLAN_STRUCTURE_TASK},
            ],
            limits,
        )
        self._prompt_history = self._seed_history(plan)

    def _seed_history(self, plan: str, include_findings: bool = False) -> list:
        assistant = f"# Initial Plan\n\n{plan}"
        if include_findings:
            assistant += f"\n\n\n# Gathered Findings\n\n{self.knowledge.get_knowledge()}"
        return [
            {"role": "system", "content": self._system},
            {"role": "user", "content": INITIAL_PLAN_INSTRUCTION},
            {"role": "assistant", "content": assistant},
            {"role": "user", "content": PLANNER_PROMPT},
        ]

    def _should_compact(self) -> bool:
        if self.compaction_max_interactions and self._interaction_counter >= self.compaction_max_interactions:
            return True
        if self.compaction_max_context_tokens:
            try:
                tokens = self.llm.count_tokens(self._prompt_history)
            except Exception:
                return False
            if tokens >= self.compaction_max_context_tokens:
                return True
        return False

    def _compact_history(self, limits: Limits) -> None:
        # regenerate a compressed plan from the running history, then reset the history to the seed
        # sequence embedding the new plan + current knowledge (findings survive compaction).
        self._prompt_history.append({"role": "user", "content": PLAN_STRUCTURE_TASK})
        plan = self._create_plan(self._prompt_history, limits)
        self._prompt_history = self._seed_history(plan, include_findings=True)
        self._interaction_counter = 0

    @override
    async def perform_round(self, limits: Limits):
        if self._should_compact():
            async with self.log.section("compacting planner history"):
                self._compact_history(limits)
        await super().perform_round(limits)
        self._interaction_counter += 1


@use_case("Autonomous LLM Active-Directory assumed-breach pentest (ported from cochise; planner/executor)")
class ADUseCase(AutonomousAgentUseCase[ADPlanner]):
    pass
