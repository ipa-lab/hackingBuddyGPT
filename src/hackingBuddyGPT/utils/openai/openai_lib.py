from dataclasses import dataclass
from typing import TypeAlias

import httpx
import instructor
import openai
from openai.types.chat import (
    ChatCompletionMessage as OpenAIChatCompletionMessage,
)
from openai.types.chat import (
    ChatCompletionMessageParam as OpenAIChatCompletionMessageParam,
)

from hackingBuddyGPT.utils import LLM, LLMResult, configurable
from hackingBuddyGPT.utils.configurable import parameter


class ChatCompletionMessage(OpenAIChatCompletionMessage):
    # this mirrors what OpenRouter returns under the hood
    reasoning: str | None = None


ChatCompletionMessageParam: TypeAlias = OpenAIChatCompletionMessageParam | ChatCompletionMessage


@configurable("openai-lib", "OpenAI Library based connection (legacy; kept only for the instructor-based web_api flow, removed in Pass 2)")
@dataclass
class OpenAILib(LLM):
    """
    Legacy connection retained solely so the ``web_api_*`` prototypes can keep using
    ``instructor`` for structured (single-action) output. All chat/completion prompting has
    moved to :class:`hackingBuddyGPT.utils.llm.LiteLLM`; this class only exposes the openai
    client and the ``instructor`` wrapper until the web_api flow is migrated to litellm
    tool-calling (Pass 2).
    """

    api_key: str = parameter(desc="OpenAI API Key", secret=True)
    model: str = parameter(desc="OpenAI model name")
    context_size: int = parameter(desc="OpenAI model context size")
    api_url: str = parameter(desc="URL of the OpenAI API", default="https://api.openai.com/v1")
    api_timeout: int = parameter(desc="Timeout for the API request", default=60)
    api_retries: int = parameter(desc="Number of retries when running into rate-limits", default=3)
    proxy: str | None = parameter(desc="Proxy URL for the API calls", default="")
    proxy_insecure: bool = parameter(
        desc="Disable TLS certificate verification for the proxy (only for intercepting proxies like Burp/mitmproxy)",
        default=False,
    )

    _client: openai.OpenAI = None

    def init(self):
        if self.proxy == "":
            self.proxy = None

        http_client = None
        if self.proxy:
            # TLS verification stays on by default; only an explicit opt-in disables it.
            http_client = httpx.Client(proxy=self.proxy, verify=not self.proxy_insecure)

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

    def get_response(self, prompt, *, capabilities=None, **kwargs) -> LLMResult:
        raise NotImplementedError(
            "OpenAILib is retained only for the instructor-based web_api flow; "
            "use hackingBuddyGPT.utils.llm.LiteLLM for chat/completion prompting."
        )

    def encode(self, query) -> list[int]:
        raise NotImplementedError("OpenAILib does not implement token encoding; use LiteLLM.count_tokens().")
