import time
import datetime
from dataclasses import dataclass

import requests
import tiktoken
from urllib.parse import urlparse

from hackingBuddyGPT.utils.configurable import configurable, parameter
from hackingBuddyGPT.utils.llm_util import LLM, LLMResult


@configurable("openai-compatible-llm-api", "OpenAI-compatible LLM API")
@dataclass
class OpenAIConnection(LLM):
    """
    While the OpenAIConnection is a configurable, it is not exported by this packages __init__.py on purpose. This is
    due to the fact, that it usually makes more sense for a finished UseCase to specialize onto one specific version of
    an OpenAI API compatible LLM.
    If you really must use it, you can import it directly from the utils.openai.openai_llm module, which will later on
    show you, that you did not specialize yet.
    """

    api_key: str = parameter(desc="OpenAI API Key", secret=True)
    model: str = parameter(desc="OpenAI model name")
    context_size: int = parameter(
        desc="Maximum context size for the model, only used internally for things like trimming to the context size"
    )
    api_url: str = parameter(desc="URL of the OpenAI API", default="https://api.openai.com")
    api_path: str = parameter(desc="Path to the OpenAI API", default="/v1/chat/completions")
    api_timeout: int = parameter(desc="Timeout for the API request", default=240)
    api_backoff: int = parameter(desc="Backoff time in seconds when running into rate-limits", default=60)
    api_retries: int = parameter(desc="Number of retries when running into rate-limits", default=3)

    def get_response(self, prompt, *, retry: int = 0,azure_retry: int = 0, **kwargs) -> LLMResult:
        if retry >= self.api_retries:
            raise Exception("Failed to get response from OpenAI API")

        if hasattr(prompt, "render"):
            prompt = prompt.render(**kwargs)

        if urlparse(self.api_url).hostname and urlparse(self.api_url).hostname.endswith(".azure.com"):
            # azure ai header
            headers = {"api-key": f"{self.api_key}"}
        else:
            # normal header
            headers = {"Authorization": f"Bearer {self.api_key}"}

        data = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}

        try:
            tic = datetime.datetime.now()
            response = requests.post(f'{self.api_url}{self.api_path}', headers=headers, json=data, timeout=self.api_timeout)

            if response.status_code == 429:
                print(f"[RestAPI-Connector] running into rate-limits, waiting for {self.api_backoff} seconds")
                time.sleep(self.api_backoff)
                return self.get_response(prompt, retry=retry + 1)

            if response.status_code == 408:
                if azure_retry < self.api_retries:
                    print("Received 408 Status Code, trying again.")
                    return self.get_response(prompt, azure_retry = azure_retry + 1)
                else:
                    raise Exception(f"Error from Gateway ({response.status_code})")

            if response.status_code != 200:
                raise Exception(f"Error from OpenAI Gateway ({response.status_code})")

        except requests.exceptions.ConnectionError:
            print("Connection error! Retrying in 5 seconds..")
            time.sleep(5)
            return self.get_response(prompt, retry=retry + 1)

        except requests.exceptions.Timeout:
            print("Timeout while contacting LLM REST endpoint")
            return self.get_response(prompt, retry=retry + 1)

        # now extract the JSON status message
        # TODO: error handling..
        response = response.json()
        result = response["choices"][0]["message"]["content"]
        tok_query = response["usage"]["prompt_tokens"]
        tok_res = response["usage"]["completion_tokens"]
        duration = datetime.datetime.now() - tic

        return LLMResult(result, prompt, result, duration, tok_query, tok_res)

    def encode(self, query) -> list[int]:
        # I know this is crappy for all non-openAI models but sadly this
        # has to be good enough for now
        if self.model.startswith("gpt-") and not self.model.startswith("gpt-4o"):
            encoding = tiktoken.encoding_for_model(self.model)
        else:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return encoding.encode(query)


@configurable("openai/gpt-3.5-turbo", "OpenAI GPT-3.5 Turbo")
@dataclass
class GPT35Turbo(OpenAIConnection):
    model: str = "gpt-3.5-turbo"
    context_size: int = 16385


@configurable("openai/gpt-4", "OpenAI GPT-4")
@dataclass
class GPT4(OpenAIConnection):
    model: str = "gpt-4"
    context_size: int = 8192


@configurable("openai/gpt-4-turbo", "OpenAI GPT-4-turbo (preview)")
@dataclass
class GPT4Turbo(OpenAIConnection):
    model: str = "gpt-4-turbo-preview"
    context_size: int = 128000


@configurable("openai/gpt-4o", "OpenAI GPT-4o")
@dataclass
class GPT4oMini(OpenAIConnection):
    model: str = "gpt-4o"
    context_size: int = 128000


@configurable("openai/gpt-4o-mini", "OpenAI GPT-4o-mini")
@dataclass
class GPT4oMini(OpenAIConnection):
    model: str = "gpt-4o-mini"
    context_size: int = 128000


@configurable("openai/o1-preview", "OpenAI o1-preview")
@dataclass
class O1Preview(OpenAIConnection):
    model: str = "o1-preview"
    context_size: int = 128000


@configurable("openai/o1-mini", "OpenAI o1-mini")
@dataclass
class O1Mini(OpenAIConnection):
    model: str = "o1-mini"
    context_size: int = 128000
