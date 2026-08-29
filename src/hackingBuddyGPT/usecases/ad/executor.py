import pathlib
from dataclasses import dataclass
from string import Template
from typing import override

from hackingBuddyGPT.capabilities.ssh_execute_command import SSHExecuteCommand
from hackingBuddyGPT.capability import Capability, function_call_capability
from hackingBuddyGPT.usecases.ad.knowledge import Knowledge
from hackingBuddyGPT.usecases.agents import ChatAgent
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.llm import LiteLLM
from hackingBuddyGPT.utils.logging import Logger

TEMPLATE_DIR = pathlib.Path(__file__).parent / "templates"
EXECUTOR_TEMPLATE = Template((TEMPLATE_DIR / "executor_prompt.md").read_text())

# descriptions for the knowledge-mutator tools (function_call_capability needs an explicit description,
# since the LLM schema is built from the function signature, not the docstring)
KNOWLEDGE_TOOL_DESCRIPTIONS = {
    "add_compromised_account": "Record an identified/compromised account (username + password or hash) with context.",
    "update_compromised_account": "Update a compromised account, identified by its numeric id from the overview table.",
    "add_entity_information": "Record a finding/lead about an entity (system, user, service, vulnerability, ...).",
    "update_entity_information": "Update information about an entity, identified by its numeric id from the overview table.",
}


def render_executor_prompt(next_step: str, next_step_context: str, max_rounds: int, knowledge: str) -> str:
    """Render the executor system/user prompt, including the knowledge block only when non-empty."""
    knowledge_block = ""
    if knowledge:
        knowledge_block = (
            "\nYou already have the following knowledge about the target environment:\n\n"
            "```markdown\n"
            f"{knowledge}"
            "```\n"
            "Be aware that this knowledge may be incomplete or incorrect.\n"
        )
    return EXECUTOR_TEMPLATE.substitute(
        next_step=next_step,
        next_step_context=next_step_context,
        max=str(max_rounds),
        knowledge_block=knowledge_block,
    )


def add_knowledge_capabilities(agent, knowledge: Knowledge) -> None:
    """Register the four knowledge mutators of ``knowledge`` as tools on ``agent``."""
    agent.add_capability(function_call_capability(
        knowledge.add_compromised_account, KNOWLEDGE_TOOL_DESCRIPTIONS["add_compromised_account"]))
    agent.add_capability(function_call_capability(
        knowledge.update_compromised_account, KNOWLEDGE_TOOL_DESCRIPTIONS["update_compromised_account"]))
    agent.add_capability(function_call_capability(
        knowledge.add_entity_information, KNOWLEDGE_TOOL_DESCRIPTIONS["add_entity_information"]))
    agent.add_capability(function_call_capability(
        knowledge.update_entity_information, KNOWLEDGE_TOOL_DESCRIPTIONS["update_entity_information"]))


@dataclass
class ADExecutor(ChatAgent):
    """Ephemeral tactical agent: built fresh for each delegated task, no memory of prior rounds.

    Its system message is the scenario; its first user message is the rendered executor prompt (the
    task, its context and a snapshot of the planner's knowledge). It drives the target through the
    ``execute_command`` SSH tool and accumulates findings in a *local* :class:`Knowledge`; it ends by
    calling ``complete`` with a technical summary.
    """

    llm: LiteLLM = None
    scenario: str = ""
    task_prompt: str = ""

    @override
    async def system_message(self, limits: Limits) -> str:
        return self.scenario

    @override
    async def before_run(self, limits: Limits):
        await super().before_run(limits)  # appends the system (scenario) message and logs it
        self._prompt_history.append({"role": "user", "content": self.task_prompt})
        await self.log.status_message(self.task_prompt)


@dataclass
class PerformTaskCapability(Capability):
    """The planner's ``perform_task`` tool: delegate one sub-task to a fresh :class:`ADExecutor`.

    Modelled on ``usecases.agents.SubAgentCapability``: it carves a sub-:class:`Limits` from the
    planner's budget, builds a worker with the SSH tool + a local Knowledge + a ``complete`` tool,
    runs it, merges the worker's dirty knowledge back into the planner's global Knowledge, and
    returns the worker's summary. The ``mitre_attack_*`` arguments make the planner categorise each
    delegation (captured in the tool-call log).
    """

    llm: LiteLLM
    log: Logger
    parent_limits: Limits
    ssh_capability: SSHExecuteCommand
    knowledge: Knowledge  # the planner's global knowledge
    scenario: str
    max_rounds: int = 25

    @override
    def describe(self) -> str:
        return (
            "Delegate one concrete sub-task of the overall objective to a worker that executes it on "
            "the target and reports back a summary. The worker has NO memory of previous rounds, so "
            "'next_step_context' must contain every detail it needs: target IP(s) and domain, the "
            "Domain Controller IP, full credentials/hashes if authentication is required, and any "
            "relevant findings from the knowledge base."
        )

    @override
    def get_name(self) -> str:
        return "perform_task"

    @override
    async def __call__(
        self,
        next_step: str,
        next_step_context: str,
        mitre_attack_tactic: str,
        mitre_attack_technique: str,
    ) -> str:
        # carve a sub-budget: the worker is bounded by its own round count, and by the planner's
        # (parent) cost/token/duration budget via the shared _parent chain.
        remaining_rounds = self.parent_limits.rounds_remaining()
        rounds = self.max_rounds if remaining_rounds is None else min(self.max_rounds, remaining_rounds)
        if rounds < 1:
            return "Could not perform the task: no rounds remaining in the run budget."
        try:
            limits = self.parent_limits.sub_limit(max_rounds=rounds, max_tokens=0, max_cost=0, max_duration=0)
        except ValueError as e:
            return f"Could not allocate a budget for the task: {e}"

        local_knowledge = Knowledge()
        prompt = render_executor_prompt(
            next_step=next_step,
            next_step_context=next_step_context,
            max_rounds=self.max_rounds - 1,
            knowledge=self.knowledge.get_knowledge(),
        )

        summary: dict[str, "str | None"] = {"text": None}

        async def complete(summary_text: str) -> str:
            """Finish the task, reporting a short technical summary back to the planner."""
            summary["text"] = summary_text
            limits.complete()
            return "Task summary recorded; the worker will now stop."

        executor = ADExecutor(log=self.log, llm=self.llm, scenario=self.scenario, task_prompt=prompt)
        executor.add_capability(self.ssh_capability, default=True)
        add_knowledge_capabilities(executor, local_knowledge)
        executor.add_capability(
            function_call_capability(
                complete,
                "Finish the task and report a short technical summary (what worked, what failed, and "
                "any findings/leads) back to the planner. Call this as soon as the task is achieved "
                "or is a clear dead end.",
                name="complete",
            )
        )

        async with self.log.section(f"worker: {next_step[:60]}"):
            await executor.before_run(limits)
            round = 1
            while not limits.reached():
                async with self.log.section(f"worker round {round}"):
                    await executor.perform_round(limits)
                round += 1

            if summary["text"] is None:
                # the worker used up its rounds without calling complete: force a final summary
                # (mirrors cochise's fallback) and account its cost against the parent budget.
                executor._prompt_history.append({
                    "role": "user",
                    "content": (
                        "Provide a short technical summary including all findings for the strategy "
                        "component. If no usable information was gained, state so and hypothesise why."
                    ),
                })
                result = self.llm.get_response(executor._prompt_history)
                self.parent_limits.register_message(result)
                summary["text"] = result.answer or (
                    "The worker did not gain any relevant information for this task."
                )

        self.knowledge.merge(local_knowledge)
        return summary["text"] + "\n\n\n" + local_knowledge.get_knowledge()
