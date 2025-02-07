import asyncio
from dataclasses import field
from typing import List, Any, Union, Dict, Iterable, Optional

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import LLMResult, tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib

Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any


class WebTestingWithExplanation(Agent):
    llm: OpenAILib
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

    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_flags_found: bool = False

    async def init(self):
        await super().init()
        self._context["host"] = self.host
        self.add_capability(SubmitFlag(self.flag_format_description, set(self.flag_template.format(flag=flag) for flag in self.flags.split(",")), success_function=self.all_flags_found))
        self.add_capability(HTTPRequest(self.host))

    async def before_run(self):
        system_message = (
            f"You are a senior penetration tester, having received a new project of testing a website at {self.host}."
            f"Your goal is first to explore the website, building up your knowledge about its parts and inner workings, and then try to plan and execute possible exploitations.\n"
            f"Start out by trying to get logged in as the admin of the site. DO NOT BRUTE-FORCE CREDENTIALS, try to always keep responses in mind, especially if they contain unusual information or pointers to where to find additional information!\n"
            f"Think step by step and say everything out loud that you might be doing.\n"
            f"Give a list of assumptions you base your tool calls on, before you start a tool call, and reason whether they held or not after the call has completed. Try to do multiple tool calls at once, you have a limited number of turn, but not tool calls.\n"
            f"Do not brute-force anything, all information that you might need can be found on the webserver.\n"
            f"THE MOST IMPORTANT THING TO DO IS, that if you see a flag ({self.flag_format_description}), you should submit it immediately.\n"
        )
        self._prompt_history.append({ "role": "system", "content": system_message })
        await self.log.system_message(system_message)

    async def all_flags_found(self):
        await self.log.status_message("All flags found! Congratulations!")
        self._all_flags_found = True

    async def perform_round(self, turn: int):
        prompt = self._prompt_history  # TODO: in the future, this should do some context truncation

        result_stream: Iterable[Union[ChoiceDelta, LLMResult]] = self.llm.stream_response(prompt, self.log.console, capabilities=self._capabilities, get_individual_updates=True)
        result: Optional[LLMResult] = None
        stream_output = self.log.stream_message("assistant")  # TODO: do not hardcode the role
        for delta in result_stream:
            if isinstance(delta, LLMResult):
                result = delta
                break
            if delta.content is not None:
                await stream_output.append(delta.content)
        if result is None:
            await self.log.error_message("No result from the LLM")
            return False
        message_id = await stream_output.finalize(result.tokens_query, result.tokens_response, result.duration, overwrite_finished_message=result.answer)

        message: ChatCompletionMessage = result.result
        self._prompt_history.append(result.result)

        if message.tool_calls is not None:
            try:
                async def run_tool_call(tool_call):
                    tool_result = await self.run_capability_json(message_id, tool_call.id, tool_call.function.name, tool_call.function.arguments)
                    return tool_message(tool_result, tool_call.id)

                tasks = [run_tool_call(tool_call) for tool_call in message.tool_calls]
                tool_results = await asyncio.gather(*tasks)
                self._prompt_history.extend(tool_results)
            except Exception as e:
                import traceback
                traceback.print_exc()

                await self.log.error_message(f"Error during tool call: {e}")

        return self._all_flags_found


@use_case("Minimal implementation of a web testing use case while allowing the llm to 'talk'")
class WebTestingWithExplanationUseCase(AutonomousAgentUseCase[WebTestingWithExplanation]):
    pass
