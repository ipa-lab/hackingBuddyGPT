import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import override

from fsspec.exceptions import asyncio
from mako.template import Template
from openai.types.chat import ChatCompletionMessageToolCall, ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from hackingBuddyGPT.capabilities.capability import (
    Capability,
    capabilities_to_simple_text_handler,
    function_call_capability,
)
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.logging import Logger, log_conversation, log_param
from hackingBuddyGPT.utils.openai.openai_lib import ChatCompletionMessageParam, OpenAILib
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection


@dataclass
class Agent(ABC):
    log: Logger = log_param

    _capabilities: dict[str, Capability] = field(default_factory=dict)
    _default_capability: Capability | None = None

    llm: OpenAIConnection = None

    async def init(self):  # noqa: B027
        pass

    async def before_run(self, limits: Limits):  # noqa: B027
        pass

    async def after_run(self):  # noqa: B027
        pass

    # callback
    @abstractmethod
    async def perform_round(self, limits: Limits):
        pass

    def add_capability(self, cap: Capability, name: str = None, default: bool = False):
        if name is None:
            name = cap.get_name()
        self._capabilities[name] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name: str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

    async def run_capability_json(
        self,
        message_id: int,
        tool_call_id: str,
        capability_name: str,
        arguments: str,
        capabilities: dict[str, Capability] | None = None,
    ) -> str:
        if capabilities is not None:
            capability = capabilities.get(capability_name, self._default_capability)
        else:
            capability = self.get_capability(capability_name)

        if capability is None:
            raise ValueError(f"Capability {capability_name} not found")

        tic = datetime.datetime.now()
        try:
            result = await capability.to_model().model_validate_json(arguments).execute()
        except Exception as e:
            import traceback

            traceback.print_exc()
            result = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        await self.log.add_tool_call(message_id, tool_call_id, capability_name, arguments, result, duration)
        return result

    async def run_tool_calls(
        self, message_id: int, message: ChatCompletionMessage
    ) -> list[ChatCompletionToolMessageParam]:
        if message.tool_calls is None:
            return []

        try:

            async def run_tool_call(tool_call: ChatCompletionMessageToolCall) -> ChatCompletionToolMessageParam:
                try:
                    tool_result = await self.run_capability_json(
                        message_id, tool_call.id, tool_call.function.name, tool_call.function.arguments
                    )
                    return llm_util.tool_message(tool_result, tool_call.id)
                except Exception as e:
                    import traceback

                    traceback.print_exc()

                    message = f"Error during tool call {tool_call.id}: {e}"
                    await self.log.status_message(message)
                    return llm_util.tool_message(message)

            return await asyncio.gather(*(run_tool_call(tool_call) for tool_call in message.tool_calls))
        except Exception as e:
            import traceback

            traceback.print_exc()

            await self.log.status_message(f"Framework error during tool calls: {e}")

        return []

    def get_capability_block(self) -> str:
        capability_descriptions, _parser = capabilities_to_simple_text_handler(self._capabilities)
        return "You can either\n\n" + "\n".join(f"- {description}" for description in capability_descriptions.values())


@dataclass
class AgentWorldview(ABC):
    @abstractmethod
    def to_template(self):
        pass

    @abstractmethod
    def update(self, capability, cmd, result):
        pass


class TemplatedAgent(Agent):
    _state: AgentWorldview = None
    _template: Template = None
    _template_size: int = 0

    def set_initial_state(self, initial_state: AgentWorldview):
        self._state = initial_state

    def set_template(self, template: str):
        self._template = Template(filename=template)
        self._template_size = self.llm.count_tokens(self._template.source)

    @override
    @log_conversation("Asking LLM for a new command...")
    async def perform_round(self, turn: int) -> bool:
        # get the next command from the LLM
        answer = self.llm.get_response(
            self._template, capabilities=self.get_capability_block(), **self._state.to_template()
        )
        message_id = self.log.call_response(answer)

        capability, cmd, result, got_root = self.run_capability_simple_text(
            message_id, llm_util.cmd_output_fixer(answer.result)
        )

        self._state.update(capability, cmd, result)

        # if we got root, we can stop the loop
        return got_root


Prompt = list[ChatCompletionMessage | ChatCompletionMessageParam]


@dataclass
class ChatAgent(Agent, ABC):
    llm: OpenAILib  # pinning the llm implementation to OpenAILib

    _role: str = "assistant"
    _prompt_history: Prompt = field(default_factory=list)

    @abstractmethod
    async def system_message(self, limits: Limits) -> str:
        raise NotImplementedError()

    @override
    async def before_run(self, limits: Limits):
        system_message = await self.system_message(limits)
        self._prompt_history.append({"role": "system", "content": system_message})
        await self.log.system_message(system_message)

    async def add_limits_message(self, limits: Limits):
        limits_str = str(limits)
        if not limits_str:
            return

        message = f"Your limits are: {limits}"
        self._prompt_history.append({"role": "user", "content": message})
        await self.log.limit_message(message)

    @override
    async def perform_round(self, limits: Limits):
        await self.add_limits_message(limits)

        message_id, result = await self.log.stream_message_from(
            self._role,
            self.llm.stream_response(
                self._prompt_history, capabilities=self._capabilities, get_individual_updates=True
            ),
        )
        limits.register_message(result)

        message: ChatCompletionMessage = result.result
        self._prompt_history.append(result.result)
        tool_call_results = await self.run_tool_calls(message_id, message)
        for tool_call_result in tool_call_results:
            self._prompt_history.append(tool_call_result)

        limits.register_round()


@dataclass
class SubAgentCapability(Capability):
    cls: type[ChatAgent]
    llm: OpenAILib
    log: Logger
    parent_limits: Limits
    capabilities: dict[str, Capability]
    role_name: str

    @override
    def describe(self) -> str:
        return f"""Spawn a subagent to work on a given task.
The subagent does not get any more information than what is given to it in the system prompt.
Therefore, you need to be very specific about what you want the subagent to do and give it all the necessary precursory information that it might need to complete the task.

For executing actions, the subagent can use the following capabilities:
- {", ".join(f"{key}: {value.describe()}" for key, value in self.capabilities.items())}

It will be presented with the capabilities of your choosing as well as a "complete" capability and it will automatically get the descriptions for the capabilities you provide.

The subagent will be run in the limits you specify (cost is in dollars, duration is in seconds) and should end by calling the "complete" capability, giving a summary back to you.
Keep in mind that the resources that the subagent uses are counted against your own total limits, and you should only set limits for things that you are also limited by.
Use limits that are below: {self.parent_limits}!
If the subagent runs into the limits, it will be given one turn to summarize the results, you will not receive anything else other than the results summarized at the end or when "complete" is being called.
Therefore, you need to specify what exactly the subagent should be reporting back with, including technical details that might be necessary for further steps."""

    @override
    async def __call__(
        self,
        system_prompt: str,
        max_rounds: int,
        max_tokens: int,
        max_cost: float,
        max_duration: int,
        capabilities: list[str],
    ) -> str:
        _result: str | None = None

        def get_selected_capabilities(capabilities: list[str], limits: Limits) -> dict[str, Capability]:
            nonlocal _result
            if "complete" in capabilities:
                capabilities.remove("complete")

            invalid_capabilities = "\n- ".join([cap for cap in capabilities if cap not in self.capabilities])
            if invalid_capabilities:
                raise ValueError(
                    f"The following capabilities are not available:\n- {invalid_capabilities}\n\nCheck the capability description for available capabilities to pass on."
                )

            selected_capabilities = {cap: self.capabilities[cap] for cap in capabilities}

            async def complete(result: str) -> str:
                nonlocal _result
                _result = result
                limits.complete()
                return "The SubAgent has completed"

            selected_capabilities["complete"] = function_call_capability(
                complete,
                "complete the task that was given to you, providing the full results as they have been requested including all further information necessary to understand it and make decisions from it.",
            )

            return selected_capabilities

        def setup_agent(system_prompt: str, limits: Limits, capabilities: list[str]) -> ChatAgent:
            selected_capabilities = get_selected_capabilities(capabilities, limits)

            class SubAgent(self.cls):
                async def system_message(self, limits: Limits) -> str:
                    return system_prompt

            return SubAgent(
                log=self.log,
                _capabilities=selected_capabilities,
                _default_capability=None,
                llm=self.llm,
                _role=self.role_name,
            )

        async def summarize_round(subagent: ChatAgent) -> str:
            nonlocal _result

            # only leave complete capability
            subagent._capabilities = {k: v for k, v in subagent._capabilities.items() if k == "complete"}
            summary_message = (
                "You have run out of rounds. THIS IS YOUR LAST ROUND, you now NEED to summarize the results of your task as it was requested in the initial system prompt!"
                "\nYour answer now (if you don't use the 'complete' capability) is going to be reported back."
                "\nDO NOT DO ANY OTHER TOOL CALLS, ONLY COMPLETE IS ALLOWED (all others have been removed)."
                "\nREMEMBER: LAST ROUND!"
            )
            subagent._prompt_history.append({"role": "user", "content": summary_message})
            await subagent.log.limit_message(summary_message)

            try:
                # TODO: we kinda give the agent a free round here without other limits...
                await subagent.perform_round(Limits(max_rounds=0, max_cost=0))
            except Exception as e:
                return f"Error summarizing round: {e}"

            if _result is None:
                # loop through the prompt history backwards until the last agent message is found
                # TODO: add in the results of the subagent's tool calls
                for message in reversed(subagent._prompt_history):
                    if not hasattr(message, "role") or message.role != self.role_name:
                        continue
                    _result = message.content

                    if has_attr(message, "tool_calls") and last_message.tool_calls:
                        tool_calls: list[ChatCompletionMessageToolCall] = last_message.tool_calls
                        _result += "\n" + "\n".join(f"{tool_call.function}: " for tool_call in tool_calls)

                if _result is None:
                    raise ValueError("Error while extracting result in summary round (this is a framework issue)")

            return _result

        try:
            limits = self.parent_limits.sub_limit(
                max_rounds=max_rounds, max_tokens=max_tokens, max_cost=max_cost, max_duration=max_duration
            )
        except ValueError as e:
            return f"Could not allocate limits: {e}"

        try:
            subagent = setup_agent(system_prompt, limits, capabilities)
        except ValueError as e:
            return f"Could not setup agent: {e}"

        async with self.log.section("subagent"):
            await subagent.before_run(limits)

            round = 1
            while not limits.reached():
                async with self.log.section(f"subagent round {round}"):
                    try:
                        await subagent.perform_round(limits)
                        round += 1
                    except Exception as e:
                        print("got subagent exception after following prompt history", subagent._prompt_history, e)
                        return f"Exception in subagent round {limits.rounds} (this is likely a framework issue): {e}"

            if _result:
                return _result
            else:
                return await summarize_round(subagent)
