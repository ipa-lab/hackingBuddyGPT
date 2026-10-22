import datetime
from dataclasses import dataclass, field

import httpx
import litellm

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capability import capabilities_to_tools
from hackingBuddyGPT.utils import LLM, LLMResult, configurable
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.llm_providers import PROVIDER_PRESETS, get_preset
from hackingBuddyGPT.utils.llm_util import user_message
from hackingBuddyGPT.utils.orcarouter.provider import ModelSelectionError, OrcaRouterProvider


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
    preset: str = parameter(
        desc="named provider preset with its own endpoint, credentials and model catalog (available: "
        + ", ".join(sorted(PROVIDER_PRESETS))
        + "); leave empty to use a plain litellm model",
        default="",
    )
    preset_api_base: str = parameter(
        desc="override the preset's inference base URL (defaults to the provider's public endpoint)",
        default="",
    )
    preset_auth_base: str = parameter(
        desc="override the preset's authentication origin (defaults to the provider's public endpoint)",
        default="",
    )
    preset_credential: str = parameter(
        desc="credential source for the preset: auto, api_key or pkce", default="auto"
    )
    embedding_model: str = parameter(
        desc="embedding model used by the RAG path; the OrcaRouter preset resolves it from the "
        "embedding-capable catalog when empty",
        default="",
    )

    # runtime state (not configuration)
    _preset_provider: OrcaRouterProvider | None = field(default=None, init=False, repr=False)

    def init(self):
        if self.proxy == "":
            self.proxy = None
        if self.provider == "":
            self.provider = None

        self._preset_provider = None
        if self.preset:
            preset = get_preset(self.preset)
            self._preset_provider = preset.create(
                api_base=self.preset_api_base or None,
                auth_base=self.preset_auth_base or None,
                credential_mode=self.preset_credential or "auto",
            )
            if self.api_key:
                self._preset_provider.set_api_key(self.api_key)
            # The model control is catalog-backed: an explicitly configured model must be
            # offered by the provider for this workspace, otherwise the run stops here.
            if not self.model:
                self.model = self._preset_provider.resolve_chat_model("")
            else:
                self.model = self._preset_provider.resolve_chat_model(self.model)
            if not self.api_key:
                self.api_key = self._preset_provider.credential().value

        if self._preset_provider is not None:
            # The project's supported proxy switch is --llm.proxy. For a named provider we build
            # the HTTP client explicitly so ambient HTTP(S)/SOCKS proxy env vars cannot intercept
            # credential exchange or inference unless the user asked for a proxy here.
            litellm.client_session = httpx.Client(
                proxy=self.proxy or None, verify=not self.proxy_insecure, trust_env=False
            )
        elif self.proxy:
            # TLS verification stays on by default; only an explicit opt-in disables it,
            # which is sometimes needed to route traffic through an intercepting proxy.
            litellm.client_session = httpx.Client(proxy=self.proxy, verify=not self.proxy_insecure)

    def get_response(self, prompt, *, capabilities: dict[str, Capability] | None = None, tool_choice=None, **kwargs) -> LLMResult:
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

        # tool_choice (e.g. "required" or {"type": "function", "function": {"name": ...}}) is only
        # meaningful when tools are offered; ignore it otherwise so a stray value can't reach the API.
        effective_tool_choice = tool_choice if tools else None

        tic = datetime.datetime.now()
        response = self.raw_completion(messages, tools=tools, tool_choice=effective_tool_choice)
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
        if self._preset_provider is not None:
            kwargs = self._preset_provider.completion_kwargs(self.model)
            try:
                return litellm.completion(
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    timeout=self.api_timeout,
                    num_retries=self.api_retries,
                    **kwargs,
                )
            except Exception as exc:
                self._preset_provider.check_response_error(exc)
                raise

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

    def embedding_config(self) -> dict:
        """Provider-specific arguments for the optional RAG embedding path."""
        if self._preset_provider is not None:
            credential = self._preset_provider.credential()
            return {
                "model": self._preset_provider.embedding_model(self.embedding_model),
                "api_key": credential.value,
                "base_url": self._preset_provider.origins.api_base,
            }
        return {
            "model": self.embedding_model or "text-embedding-3-large",
            "api_key": self.api_key,
        }

    def count_tokens(self, query) -> int:
        if self._preset_provider is not None:
            # The provider model ids are not in litellm's bundled tokenizer map; a bounded
            # character estimate keeps prompt trimming working without a network round trip.
            text = str(query) if not isinstance(query, list) else " ".join(str(item) for item in query)
            return max(1, len(text) // 4)
        if isinstance(query, list):
            return litellm.token_counter(model=self.model, messages=query)
        return litellm.token_counter(model=self.model, text=str(query))

    def encode(self, query) -> list[int]:
        # litellm does token counting model-side via count_tokens(); raw token ids are not needed.
        raise NotImplementedError("LiteLLM counts tokens via count_tokens(); encode() is not used")
