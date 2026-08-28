import datetime
from dataclasses import dataclass

import httpx
import litellm

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capability import capabilities_to_tools
from hackingBuddyGPT.utils import LLM, LLMResult, configurable
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.llm_util import user_message


@configurable("litellm", "litellm-based unified LLM connection")
@dataclass
class LiteLLM(LLM):
    """
    Single LLM upstream for the whole project, built on litellm.

    It serves both prompt styles through one ``get_response`` entry point:

    - a **chat message list** (``[{"role": ...}, ...]``) is sent as-is, and any
      ``capabilities`` dict is turned into function-calling ``tools``. The returned
      ``LLMResult.result`` is the assistant *message object* (with ``.tool_calls``).
    - a **string / Mako template** is rendered (with the given ``**kwargs``) and wrapped
      as a single user message. The returned ``LLMResult.result`` is the answer *string*.
    """

    api_key: str = parameter(desc="API key for the upstream", secret=True)
    model: str = parameter(desc="model name in litellm format, e.g. 'gpt-4o' or 'openrouter/anthropic/claude-3.5-sonnet'")
    context_size: int = parameter(desc="maximum context size of the model (used for prompt trimming)")
    api_base: str = parameter(desc="base URL of the API", default="https://openrouter.ai/api")
    api_timeout: int = parameter(desc="timeout for a single request in seconds", default=300)
    api_retries: int = parameter(desc="number of retries when running into rate-limits", default=3)
    provider: str | None = parameter(
        desc="OpenRouter provider routing, only useful when using OpenRouter, otherwise leave empty",
        default="",
    )
    proxy: str | None = parameter(desc="Proxy URL for the API calls", default="")
    proxy_insecure: bool = parameter(
        desc="Disable TLS certificate verification for the proxy (only for intercepting proxies like Burp/mitmproxy)",
        default=False,
    )

    def init(self):
        if self.proxy == "":
            self.proxy = None
        if self.provider == "":
            self.provider = None

        if self.proxy:
            # TLS verification stays on by default; only an explicit opt-in disables it,
            # which is sometimes needed to route traffic through an intercepting proxy.
            litellm.client_session = httpx.Client(proxy=self.proxy, verify=not self.proxy_insecure)

    def get_response(self, prompt, *, capabilities: dict[str, Capability] | None = None, **kwargs) -> LLMResult:
        chat_style = isinstance(prompt, list)

        if chat_style:
            messages = prompt
            tools = capabilities_to_tools(capabilities) if capabilities else None
        else:
            if hasattr(prompt, "render"):
                render_kwargs = dict(kwargs)
                if capabilities is not None:
                    render_kwargs["capabilities"] = capabilities
                content = prompt.render(**render_kwargs)
            else:
                content = str(prompt)
            messages = [user_message(content)]
            tools = None

        tic = datetime.datetime.now()
        response = self.raw_completion(messages, tools=tools)
        duration = datetime.datetime.now() - tic

        message = response.choices[0].message
        usage = response.usage

        tokens_reasoning = 0
        details = getattr(usage, "completion_tokens_details", None)
        if details is not None:
            tokens_reasoning = getattr(details, "reasoning_tokens", 0) or 0

        try:
            usage_details = usage.model_dump_json()
        except Exception:
            usage_details = ""

        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = getattr(usage, "cost", 0) or 0

        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        content = message.content or ""
        result = message if chat_style else content

        model_name = getattr(response, "model", None) or self.model
        try:
            finish_reason = response.choices[0].finish_reason or ""
        except Exception:
            finish_reason = ""
        try:
            provider = (getattr(response, "_hidden_params", None) or {}).get("custom_llm_provider", "") or ""
        except Exception:
            provider = ""

        return LLMResult(
            result,
            str(prompt),
            content,
            reasoning,
            duration,
            usage.prompt_tokens,
            usage.completion_tokens,
            tokens_reasoning,
            usage_details,
            cost,
            model=model_name,
            finish_reason=finish_reason,
            provider=provider,
        )

    def raw_completion(self, messages, *, tools=None, tool_choice=None):
        """
        Make a completion call and return the raw litellm ``ModelResponse``.

        This is the single place that holds the upstream configuration (model, credentials,
        provider routing, retries). It is used both by :meth:`get_response` and by callers
        that need the unprocessed completion, e.g. the web_api tool-calling flow.
        """
        extra_body = {"provider": {"only": [self.provider]}} if self.provider else None
        return litellm.completion(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            # api_base=self.api_base, TODO: why is thi snot working anymore
            api_key=self.api_key,
            timeout=self.api_timeout,
            num_retries=self.api_retries,
            extra_body=extra_body,
        )

    def count_tokens(self, query) -> int:
        if isinstance(query, list):
            return litellm.token_counter(model=self.model, messages=query)
        return litellm.token_counter(model=self.model, text=str(query))

    def encode(self, query) -> list[int]:
        # litellm does token counting model-side via count_tokens(); raw token ids are not needed.
        raise NotImplementedError("LiteLLM counts tokens via count_tokens(); encode() is not used")
