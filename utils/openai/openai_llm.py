import time

import requests

from dataclasses import dataclass

import tiktoken

from utils.configurable import configurable
from utils.llm_util import LLMResult, LLM


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
    api_key: str
    model: str
    context_size: int
    api_url: str = "https://api.openai.com"
    api_timeout: int = 240
    api_backoff: int = 60
    api_retries: int = 3

    def get_response(self, prompt, *, retry: int = 0, **kwargs) -> LLMResult:
        if retry >= self.api_retries:
            raise Exception("Failed to get response from OpenAI API")

        if hasattr(prompt, "render"):
            prompt = prompt.render(**kwargs)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {'model': self.model, 'messages': [{'role': 'user', 'content': prompt}]}

        try:
            tic = time.perf_counter()
            response = requests.post(f'{self.api_url}/v1/chat/completions', headers=headers, json=data, timeout=self.api_timeout)
            if response.status_code == 429:
                print(f"[RestAPI-Connector] running into rate-limits, waiting for {self.api_backoff} seconds")
                time.sleep(self.api_backoff)
                return self.get_response(prompt, retry=retry+1)

            if response.status_code != 200:
                raise Exception(f"Error from OpenAI Gateway ({response.status_code}")

        except requests.exceptions.ConnectionError:
            print("Connection error! Retrying in 5 seconds..")
            time.sleep(5)
            return self.get_response(prompt, retry=retry+1)

        except requests.exceptions.Timeout:
            print("Timeout while contacting LLM REST endpoint")
            return self.get_response(prompt, retry=retry+1)

        # now extract the JSON status message
        # TODO: error handling..
        toc = time.perf_counter()
        response = response.json()
        result = response['choices'][0]['message']['content']
        tok_query = response['usage']['prompt_tokens']
        tok_res = response['usage']['completion_tokens']

        return LLMResult(result, prompt, result, toc - tic, tok_query, tok_res)

    def encode(self, query) -> list[int]:
        return tiktoken.encoding_for_model(self.model).encode(query)


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
