import instructor
import openai
import tiktoken
import time
from dataclasses import dataclass

from hackingBuddyGPT.utils import LLM, configurable, LLMResult
from hackingBuddyGPT.utils.configurable import parameter


@configurable("openai-lib", "OpenAI Library based connection")
@dataclass
class OpenAILib(LLM):
    api_key: str = parameter(desc="OpenAI API Key")
    model: str = parameter(desc="OpenAI model name")
    context_size: int = parameter(desc="OpenAI model context size")
    api_url: str = parameter(desc="URL of the OpenAI API", default="https://api.openai.com/v1")
    api_timeout: int = parameter(desc="Timeout for the API request", default=60)
    api_retries: int = parameter(desc="Number of retries when running into rate-limits", default=3)

    _client: openai.OpenAI = None

    def init(self):
        self._client = openai.OpenAI(api_key=self.api_key, base_url=self.api_url, timeout=self.api_timeout, max_retries=self.api_retries)

    @property
    def client(self) -> openai.OpenAI:
        return self._client

    @property
    def instructor(self) -> instructor.Instructor:
        return instructor.from_openai(self.client)

    def get_response(self, prompt, *, capabilities=None, **kwargs) -> LLMResult:
        if isinstance(prompt, str) or hasattr(prompt, "render"):
            prompt = {"role": "user", "content": prompt}

        if isinstance(prompt, dict):
            prompt = [prompt]

        for k, v in prompt.items():
            if hasattr(v["content"], "render"):
                prompt[k] = v.render(**kwargs)

        tic = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.model,
            messages=prompt
        )
        toc = time.perf_counter()

        return LLMResult(
            response.choices[0].message.content,
            str(prompt),
            response.choices[0].message.content,
            toc-tic,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )

    def encode(self, query) -> list[int]:
        return tiktoken.encoding_for_model(self.model).encode(query)
