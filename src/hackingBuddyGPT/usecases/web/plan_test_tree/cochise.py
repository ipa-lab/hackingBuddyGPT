### UNTESTED!
import asyncio
from dataclasses import dataclass, field
from os import path
from typing import Awaitable, List, Any, Union, Dict, Iterable, Optional, Callable

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage, ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from hackingBuddyGPT.capabilities import Capability, function_capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import LLMResult, tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.logging import GlobalLogger
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


from jinja2 import Template


Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any


async def stream_llm(
    prompt: Iterable[ChatCompletionMessageParam],
    role: str,
    llm: OpenAILib,
    log: GlobalLogger,
    capabilities: Optional[Dict[str, Capability]] = None,
) -> tuple[Optional[int], Optional[LLMResult]]:
    result_stream: Iterable[Union[ChoiceDelta, LLMResult]] = llm.stream_response(
        prompt, log.console, capabilities=capabilities, get_individual_updates=True
    )
    stream_output = log.stream_message(role)
    for delta in result_stream:
        if isinstance(delta, LLMResult):
            message_id = await stream_output.finalize(
                delta.tokens_query,
                delta.tokens_response,
                delta.tokens_reasoning,
                delta.usage_details,
                delta.cost,
                delta.duration,
                overwrite_finished_message=delta.answer,
            )
            return message_id, delta
        if delta.content is not None:
            await stream_output.append(delta.content)

    await log.error_message("No result from the LLM")
    return None, None


async def run_tool_calls(
    message_id: int, tool_calls: Optional[list[ChatCompletionMessageToolCall]], log: GlobalLogger, run_capability
) -> list[ChatCompletionToolMessageParam]:
    if tool_calls is None:
        return []

    async def run_tool_call(tool_call) -> ChatCompletionToolMessageParam:
        try:
            tool_result = await run_capability(
                message_id, tool_call.id, tool_call.function.name, tool_call.function.arguments
            )
            return tool_message(tool_result, tool_call.id)
        except Exception as e:
            import traceback

            traceback.print_exc()

            await log.error_message(f"Error during tool call: {e}")
            return tool_message(f"Error during tool call: {e}", tool_call.id)

    tasks = [run_tool_call(tool_call) for tool_call in tool_calls]
    return list(await asyncio.gather(*tasks))


class Cochise(Agent):
    llm: OpenAILib
    execution_llm: OpenAILib = parameter(desc="The LLM to use for task execution", default=None)

    host: str = parameter(desc="The host to test", default="http://localhost")
    flag_format_description: str = parameter(
        desc="Description of the flag provided to the LLM",
        default="a string starting with 'FLAG.' and ending with '.GALF'",
    )
    flag_template: str = parameter(
        desc="The template of the flags, whereby {flag} is replaced with the flags",
        default="FLAG.{flag}.GALF",
    )
    flags: str = parameter(
        desc="A comma (,) separated list of flags to find",
        default="hostname,dir,username,rootfile,secretfile,adminpass",
    )
    max_task_rounds: int = parameter(desc="Number of rounds that should be spent on a task at max", default=10)

    _context: Context = field(default_factory=lambda: {"notes": list()})
    _plan: str = field(default_factory=lambda: "")
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_flags_found: bool = False
    _last_tasks_results = None

    async def init(self):
        await super().init()
        self._context["host"] = self.host
        self.add_capability(
            SubmitFlag(
                self.flag_format_description,
                set(self.flag_template.format(flag=flag) for flag in self.flags.split(",")),
                success_function=self.all_flags_found,
            )
        )

    async def all_flags_found(self):
        await self.log.status_message("All flags found! Congratulations!")
        self._all_flags_found = True

    @property
    def scenario(self) -> str:
        return (
            f"You are a senior penetration tester, having received a new project of testing a website at {self.host}."
            f"Your goal is first to explore the website, building up your knowledge about its parts and inner workings, and then try to plan and execute possible exploitations.\n"
            f"Start out by trying to get logged in as the admin of the site. DO NOT BRUTE-FORCE CREDENTIALS, try to always keep responses in mind, especially if they contain unusual information or pointers to where to find additional information!\n"
            f"Think step by step and say everything out loud that you might be doing.\n"
            f"Give a list of assumptions you base your tool calls on, before you start a tool call, and reason whether they held or not after the call has completed. Try to do multiple tool calls at once, you have a limited number of turn, but not tool calls.\n"
            f"Do not brute-force anything, all information that you might need can be found on the webserver.\n"
            f"THE MOST IMPORTANT THING TO DO IS, that if you see a flag ({self.flag_format_description}), you should submit it immediately.\n"
        )

    def update_prompt(self) -> str:
        template_path = path.join(path.dirname(__file__), "prompts/ptt_update_plan.md")
        with open(template_path, "r") as f:
            template_text = f.read()
        template = Template(template_text)
        return template.render(scenario=self.scenario, plan=self._plan, tasks=self._last_tasks_results)

    def next_task_prompt(self) -> str:
        template_path = path.join(path.dirname(__file__), "prompts/ptt_next_task.md")
        with open(template_path, "r") as f:
            template_text = f.read()
        template = Template(template_text)
        return template.render(scenario=self.scenario, plan=self._plan)

    async def perform_round(self, turn: int):
        update_prompt = self.update_prompt()
        await self.log.system_message(update_prompt)

        plan_message_id, plan_result = await stream_llm(
            [{"role": "system", "content": update_prompt}],
            "assistant",
            self.llm,
            self.log,
        )
        if plan_message_id is None or plan_result is None:
            return False

        self._plan = plan_result.answer

        next_task_capabilities: Dict[str, Capability] = {
            "execute_task": ExecuteTask(
                self.execution_llm,
                self.log,
                self.max_task_rounds,
                {**self._capabilities, "HTTPRequest": HTTPRequest(self.host)},
                self.make_run_capability_json,
            ),
        }

        next_task_prompt = self.next_task_prompt()
        await self.log.system_message(next_task_prompt)

        task_message_id, task_result = await stream_llm(
            [{"role": "system", "content": next_task_prompt}],
            "assistant",
            self.llm,
            self.log,
            next_task_capabilities,
        )
        if task_message_id is None or task_result is None:
            return False

        self._last_tasks_results = await run_tool_calls(
            task_message_id,
            task_result.result.tool_calls,
            self.log,
            self.make_run_capability_json(next_task_capabilities),
        )

        return self._all_flags_found


@dataclass
class ExecuteTask(Capability):
    llm: OpenAILib
    log: GlobalLogger
    max_rounds: int
    capabilities: Dict[str, Capability]
    make_run_capability_json: Callable[[Dict[str, Capability]], Callable[[int, str, str, str], Awaitable[str]]]

    _summary: Optional[str] = None

    def describe(self) -> str:
        return "Passes a given task on to another agent to be executed. Needs all the information and context about the task to be able to solve it independently."

    async def finish_with_summary(self, summary: str) -> str:
        self._summary = summary
        return "Done"

    async def __call__(self, task_name: str, task_description: str) -> str:
        template_path = path.join(path.dirname(__file__), "prompts/ptt_subtask.md")
        with open(template_path, "r") as f:
            template_text = f.read()
        template = Template(template_text)
        extended_task_description = template.render(task=task_description)

        result = await self.execute(task_name, extended_task_description)
        return f"## {task_name}\n### Prompt\n{task_description}\n\n### Results\n{result}"

    async def execute(self, task_name: str, task_description: str) -> str:
        task_round = 1
        prompt_history: list[ChatCompletionMessageParam] = [{"role": "system", "content": task_description}]
        await self.log.system_message(task_description)
        finish_capabilities = {
            "finish_with_summary": function_capability(
                self.finish_with_summary,
                "Finish the current task with a summary of the steps taken and the resulting progress",
            )
        }
        self.capabilities.update(finish_capabilities)

        while task_round <= self.max_rounds:
            task_round += 1
            message_id, result = await stream_llm(
                prompt_history, f"assistant-{task_name}", self.llm, self.log, self.capabilities
            )
            if message_id is None or result is None:
                return "Failed to execute task, did not get response from agent"

            prompt_history.extend(
                [
                    result.result,
                    *await run_tool_calls(
                        message_id, result.result.tool_calls, self.log, self.make_run_capability_json(self.capabilities)
                    ),
                ]
            )

            if self._summary is not None:
                return self._summary

        for _ in range(3):
            prompt_history.append(
                {
                    "role": "user",
                    "content": "You have reached the maximum number of rounds. Please summarize the steps taken and the resulting progress via the `finish_with_summary` function.",
                }
            )

            message_id, result = await stream_llm(
                prompt_history, f"assistant-{task_name}", self.llm, self.log, finish_capabilities
            )
            if message_id is None or result is None:
                return "Failed to execute task, did not get response from agent"

            prompt_history.extend(
                [
                    result.result,
                    *await run_tool_calls(
                        message_id,
                        result.result.tool_calls,
                        self.log,
                        self.make_run_capability_json(finish_capabilities),
                    ),
                ]
            )

            if self._summary is not None:
                return self._summary

        return "Failed to execute task, reached maximum number of rounds without summary"


@use_case("Port of the original Cochise use case")
class CochiseUseCase(AutonomousAgentUseCase[Cochise]):
    pass
