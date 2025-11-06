import datetime
import httpx
from dataclasses import dataclass
from typing import Iterable, Optional, Union, TypeAlias

import json
import instructor
import openai
import tiktoken
from dataclasses import dataclass
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletionMessage as OpenAIChatCompletionMessage,
    ChatCompletionMessageParam as OpenAIChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.chat.chat_completion_message_tool_call import Function
from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_tools
from hackingBuddyGPT.utils import LLM, LLMResult, configurable
from hackingBuddyGPT.utils.configurable import parameter


class ChatCompletionMessage(OpenAIChatCompletionMessage):
    # this mirrors what OpenRouter returns under the hood
    reasoning: str | None = None


ChatCompletionMessageParam: TypeAlias = OpenAIChatCompletionMessageParam | ChatCompletionMessage


@configurable("openai-lib", "OpenAI Library based connection")
@dataclass
class OpenAILib(LLM):
    api_key: str = parameter(desc="OpenAI API Key", secret=True)
    model: str = parameter(desc="OpenAI model name")
    context_size: int = parameter(desc="OpenAI model context size")
    api_url: str = parameter(desc="URL of the OpenAI API", default="https://api.openai.com/v1")
    api_timeout: int = parameter(desc="Timeout for the API request", default=60)
    api_retries: int = parameter(desc="Number of retries when running into rate-limits", default=3)
    provider: str | None = parameter(
        desc="OpenRouter provider, only useful if using OpenRouter, otherwise this might make the requests fail",
        default="",
    )
    proxy: str | None = parameter(desc="Proxy URL for the API calls", default="")

    _client: openai.OpenAI = None
    _can_stream: bool = True

    def init(self):
        if self.proxy == "":
            self.proxy = None
        if self.provider == "":
            self.provider = None

        http_client = None
        if self.proxy:
            http_client = httpx.Client(proxy=self.proxy, verify=False)

        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            timeout=self.api_timeout,
            max_retries=self.api_retries,
            http_client=http_client,
        )

    @property
    def client(self) -> openai.OpenAI:
        return self._client

    @property
    def instructor(self) -> instructor.Instructor:
        return instructor.from_openai(self.client)

    def get_response(self, prompt, *, capabilities: dict[str, Capability] | None = None, **kwargs) -> LLMResult:
        """# TODO: re-enable compatibility layer
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

        if self.provider is not None:
            extra_body = {"provider": {"only": [self.provider]}}
        else:
            extra_body = None

        tic = datetime.datetime.now()
        processed_messages = self.process_messages(prompt)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=processed_messages,
            tools=tools,
            extra_body=extra_body,
        )
        duration = datetime.datetime.now() - tic
        message = response.choices[0].message

        tokens_reasoning = 0
        if response.usage.completion_tokens_details:
            tokens_reasoning = response.usage.completion_tokens_details.reasoning_tokens

        usage_details = ""
        try:
            usage_details = response.usage.model_dump_json()
        except Exception:
            try:
                usage_details = json.dumps(response.usage)
            except Exception:
                pass

        cost = 0
        if hasattr(response.usage, "cost"):
            cost = response.usage.cost

        return LLMResult(
            message,
            str(prompt),
            message.content,
            message.reasoning,
            duration,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            tokens_reasoning,
            usage_details,
            cost,
        )

    def stream_response(
        self,
        prompt: Iterable[ChatCompletionMessageParam],
        capabilities: dict[str, Capability] | None = None,
        get_individual_updates: bool = False,
    ) -> LLMResult | Iterable[ChoiceDelta | LLMResult]:
        if not self._can_stream:
            result = self.get_response(prompt, capabilities=capabilities)
            if get_individual_updates:
                return [result]
            return result

        try:
            generator = self._stream_response(prompt, capabilities)

            if get_individual_updates:
                return generator

            return list(generator)[-1]

        except openai.BadRequestError as e:
            if "'stream' does not support true with this model" in str(e):
                print("WARNING: Got an error that the model does not support streaming, falling back to non-streaming")
                self._can_stream = False
                return self.stream_response(prompt, capabilities, get_individual_updates)

            raise e

    def _stream_response(
        self,
        prompt: Iterable[ChatCompletionMessageParam],
        capabilities: dict[str, Capability] | None = None,
    ) -> Iterable[ChoiceDelta | LLMResult]:
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

        message = ChatCompletionMessage(role="assistant", content="", tool_calls=[])
        usage: Optional[CompletionUsage] = None

        for chunk in chunks:
            if len(chunk.choices) > 0:
                if len(chunk.choices) > 1:
                    print("WARNING: Got more than one choice in the stream response")

                delta = chunk.choices[0].delta
                if delta.role is not None and delta.role != message.role:
                    print(f"WARNING: Got a role change to '{delta.role}' in the stream response")

                if delta.content is not None and len(delta.content) > 0:
                    message.content += delta.content

                if hasattr(delta, "reasoning") and delta.reasoning is not None and len(delta.reasoning) > 0:
                    if message.reasoning is None:
                        message.reasoning = ""
                    message.reasoning += delta.reasoning

                if delta.tool_calls is not None and len(delta.tool_calls) > 0:
                    for tool_call in delta.tool_calls:
                        if len(message.tool_calls) <= tool_call.index:
                            if len(message.tool_calls) != tool_call.index:
                                print(
                                    f"WARNING: Got a tool call with index {tool_call.index} but expected {len(message.tool_calls)}"
                                )
                                return
                            if tool_call.function.name is None:
                                print(f"WARNING: Got a tool call with no function name")
                                continue
                            if tool_call.function.arguments is None:
                                print(f"WARNING: Got a tool call with no arguments")
                                continue

                            message.tool_calls.append(
                                ChatCompletionMessageToolCall(
                                    id=tool_call.id,
                                    function=Function(
                                        name=tool_call.function.name, arguments=tool_call.function.arguments
                                    ),
                                    type="function",
                                )
                            )
                        else:
                            message.tool_calls[tool_call.index].function.arguments += tool_call.function.arguments

                yield delta

            if chunk.usage is not None:
                usage = chunk.usage

        if usage is None:
            print("WARNING: Did not get usage information in the stream response")
            usage = CompletionUsage(completion_tokens=0, prompt_tokens=0, total_tokens=0)

        if len(message.tool_calls) == 0:  # the openAI API does not like getting empty tool call lists
            message.tool_calls = None

        reasoning_tokens = 0
        if usage.completion_tokens_details:
            reasoning_tokens = usage.completion_tokens_details.reasoning_tokens

        usage_details = ""
        try:
            usage_details = usage.model_dump_json()
        except Exception:
            try:
                usage_details = json.dumps(usage)
            except Exception:
                pass

        cost = 0
        if hasattr(usage, "cost"):
            cost = usage.cost

        toc = datetime.datetime.now()
        yield LLMResult(
            message,
            str(prompt),
            message.content,
            message.reasoning,
            toc - tic,
            usage.prompt_tokens,
            usage.completion_tokens,
            reasoning_tokens,
            usage_details,
            cost,
        )

    def encode(self, query) -> list[int]:
        return tiktoken.encoding_for_model(self.model).encode(query)
