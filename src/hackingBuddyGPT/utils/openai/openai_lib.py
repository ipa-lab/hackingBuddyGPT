import datetime
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Union

import instructor
import openai
import tiktoken
from dataclasses import dataclass
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.chat.chat_completion_message_tool_call import Function
from rich.console import Console

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capability import capabilities_to_tools
from hackingBuddyGPT.utils import LLM, LLMResult, configurable
from hackingBuddyGPT.utils.configurable import parameter


@configurable("openai-lib", "OpenAI Library based connection")
@dataclass
class OpenAILib(LLM):
    api_key: str = parameter(desc="OpenAI API Key", secret=True)
    model: str = parameter(desc="OpenAI model name")
    context_size: int = parameter(desc="OpenAI model context size")
    api_url: str = parameter(desc="URL of the OpenAI API", default="https://api.openai.com/v1")
    api_timeout: int = parameter(desc="Timeout for the API request", default=60)
    api_retries: int = parameter(desc="Number of retries when running into rate-limits", default=3)

    _client: openai.OpenAI = None

    def init(self):
        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            timeout=self.api_timeout,
            max_retries=self.api_retries,
        )

    @property
    def client(self) -> openai.OpenAI:
        return self._client

    @property
    def instructor(self) -> instructor.Instructor:
        return instructor.from_openai(self.client)

    def get_response(self, prompt, *, capabilities: Optional[Dict[str, Capability] ] = None, **kwargs) -> LLMResult:
        """  # TODO: re-enable compatibility layer
        if isinstance(prompt, str) or hasattr(prompt, "render"):
            prompt = {"role": "user", "content": prompt}

        if isinstance(prompt, dict):
            prompt = [prompt]

        for i, v in enumerate(prompt):
            if hasattr(v, "content") and hasattr(v["content"], "render"):
                prompt[i]["content"] = v.render(**kwargs)
        """

        tools = None
        if capabilities:
            tools = capabilities_to_tools(capabilities)

        tic = datetime.datetime.now()
        response = self._client.chat.completions.create(
            model=self.model,
            messages=prompt,
            tools=tools,
        )
        duration = datetime.datetime.now() - tic
        message = response.choices[0].message

        return LLMResult(
            message,
            str(prompt),
            message.content,
            duration,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )

    def stream_response(self, prompt: Iterable[ChatCompletionMessageParam], console: Console, capabilities: Dict[str, Capability] = None, get_individual_updates=False) -> Union[LLMResult, Iterable[Union[ChoiceDelta, LLMResult]]]:
        generator = self._stream_response(prompt, console, capabilities)

        if get_individual_updates:
            return generator

        return list(generator)[-1]

    def _stream_response(self, prompt: Iterable[ChatCompletionMessageParam], console: Console, capabilities: Dict[str, Capability] = None) -> Iterable[Union[ChoiceDelta, LLMResult]]:
        tools = None
        if capabilities:
            tools = capabilities_to_tools(capabilities)

        tic = datetime.datetime.now()
        chunks = self._client.chat.completions.create(
            model=self.model,
            messages=prompt,
            tools=tools,
            stream=True,
            stream_options={"include_usage": True},
        )

        state = None
        message = ChatCompletionMessage(role="assistant", content="", tool_calls=[])
        usage: Optional[CompletionUsage] = None

        for chunk in chunks:
            outputs = 0
            if len(chunk.choices) > 0:
                if len(chunk.choices) > 1:
                    print("WARNING: Got more than one choice in the stream response")

                delta = chunk.choices[0].delta
                if delta.role is not None and delta.role != message.role:
                    print(f"WARNING: Got a role change to '{delta.role}' in the stream response")

                if delta.content is not None:
                    message.content += delta.content
                    if state != "content":
                        state = "content"
                        console.print("\n\n[bold blue]ASSISTANT:[/bold blue]")
                    console.print(delta.content, end="")
                    outputs += 1

                if delta.tool_calls is not None and len(delta.tool_calls) > 0:
                    if state != "tool_call":
                        state = "tool_call"
                    for tool_call in delta.tool_calls:
                        if len(message.tool_calls) <= tool_call.index:
                            if len(message.tool_calls) != tool_call.index:
                                print(
                                    f"WARNING: Got a tool call with index {tool_call.index} but expected {len(message.tool_calls)}"
                                )
                                return
                            console.print(f"\n\n[bold red]TOOL CALL - {tool_call.function.name}:[/bold red]")
                            message.tool_calls.append(
                                ChatCompletionMessageToolCall(
                                    id=tool_call.id,
                                    function=Function(
                                        name=tool_call.function.name, arguments=tool_call.function.arguments
                                    ),
                                    type="function",
                                )
                            )
                        console.print(tool_call.function.arguments, end="")
                        message.tool_calls[tool_call.index].function.arguments += tool_call.function.arguments
                        outputs += 1

                yield delta

            if chunk.usage is not None:
                usage = chunk.usage

            if outputs > 1:
                print("WARNING: Got more than one output in the stream response")

        console.print()
        if usage is None:
            print("WARNING: Did not get usage information in the stream response")
            usage = CompletionUsage(completion_tokens=0, prompt_tokens=0, total_tokens=0)

        if len(message.tool_calls) == 0:  # the openAI API does not like getting empty tool call lists
            message.tool_calls = None

        toc = datetime.datetime.now()
        yield LLMResult(
            message,
            str(prompt),
            message.content,
            toc - tic,
            usage.prompt_tokens,
            usage.completion_tokens,
        )

    def encode(self, query) -> list[int]:
        return tiktoken.encoding_for_model(self.model).encode(query)
