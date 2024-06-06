import time

from dataclasses import dataclass, field
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from rich.panel import Panel
from typing import List, Any, Union, Dict

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.common_patterns import RoundBasedUseCase
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.utils import LLMResult, tool_message, ui
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib
from hackingBuddyGPT.usecases import use_case

import pydantic_core

Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any


@use_case("simple_web_api_testing", "Minimal implementation of a web api testing use case")
@dataclass
class SimpleWebAPITesting(RoundBasedUseCase):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    # Parameter specifying the pattern description for expected HTTP methods in the API response
    http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.)."
    )

    # Parameter specifying the template used to format HTTP methods in API requests
    http_method_template: str = parameter(
        desc="Template used to format HTTP methods in API requests. The {method} placeholder will be replaced by actual HTTP method names.",
        default="{method}"
    )

    # Parameter specifying the expected HTTP methods as a comma-separated list
    http_methods: str = parameter(
        desc="Comma-separated list of HTTP methods expected to be used in the API response.",
        default="GET,POST,PUT,DELETE"
    )

    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    def init(self):
        super().init()
        self._prompt_history.append(
            {
                "role": "system",
                "content": f"You're a seasoned API tester tasked with evaluating the REST APIs of a website hosted at {self.host}. "
                           f"Your primary objective is to thoroughly explore the APIs, understanding their endpoints, parameters, and responses, and then devise and execute potential exploits.\n"
                           f"Be diligent in documenting your findings as you navigate through the APIs..\n"
                           f"Avoid resorting to brute-force tactics. All necessary information can be obtained from the API endpoints themselves.\n"
                           f"Remember, if you encounter a http methods ({self.http_method_description}), promptly submit it as it is of utmost importance."
            })
        self.prompt_engineer = PromptEngineer(strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                                              api_key=self.llm.api_key,
                                              history=self._prompt_history)

        self._context["host"] = self.host
        sett = set(self.http_method_template.format(method=method) for method in self.http_methods.split(","))
        flag = SubmitFlag(self.http_method_description,
                                      sett,
                                      success_function=self.all_http_methods_found)
        print(f'Valid flags:{flag.valid_flags}')
        self._capabilities = {
            "submit_http_method": flag,
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(self._context["notes"]),
        }

    def all_http_methods_found(self):
        self.console.print(Panel("All HTTP methods found! Congratulations!", title="system"))
        self._all_http_methods_found = True

    def perform_round(self, turn: int):
        with self.console.status("[bold green]Asking LLM for a new command..."):
            # generate prompt
            prompt = self.prompt_engineer.generate_prompt()


            tic = time.perf_counter()
            response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model,
                                                                                               messages=prompt,
                                                                                               response_model=capabilities_to_action_model(
                                                                                                   self._capabilities))
            toc = time.perf_counter()

            message = completion.choices[0].message
            tool_call_id = message.tool_calls[0].id
            command = pydantic_core.to_json(response).decode()
            self.console.print(Panel(command, title="assistant"))
            self._prompt_history.append(message)

            answer = LLMResult(completion.choices[0].message.content, str(prompt),
                               completion.choices[0].message.content, toc - tic, completion.usage.prompt_tokens,
                               completion.usage.completion_tokens)

        with self.console.status("[bold green]Executing that command..."):
            result = response.execute()
            self.console.print(Panel(result, title="tool"))
            result_str = self.parse_http_status_line(result)
            self._prompt_history.append(tool_message(result_str, tool_call_id))


        self.log_db.add_log_query(self._run_id, turn, command, result, answer)
        return self._all_http_methods_found

    def parse_http_status_line(self, status_line):
        if status_line is None or status_line == "Not a valid flag":
            return status_line
        else:
            # Split the status line into components
            parts = status_line.split(' ', 2)

            # Check if the parts are at least three in number
            if len(parts) >= 3:
                protocol = parts[0]  # e.g., "HTTP/1.1"
                status_code = parts[1]  # e.g., "200"
                status_message = parts[2].split("\r\n")[0]  # e.g., "OK"
                print(f'status code:{status_code}, status msg:{status_message}')
                return str(status_code + " " + status_message)
            else:
                raise ValueError("Invalid HTTP status line")
