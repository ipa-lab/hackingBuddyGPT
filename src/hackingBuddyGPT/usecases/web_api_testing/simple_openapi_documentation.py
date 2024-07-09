import datetime
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Union, Dict

import pydantic_core
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from rich.panel import Panel

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.submit_http_method import SubmitHTTPMethod
from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.common_patterns import RoundBasedUseCase
from hackingBuddyGPT.usecases.web_api_testing.documentation_handler import DocumentationHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.utils import LLMResult, tool_message, ui
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib
from hackingBuddyGPT.usecases.base import use_case
import hackingBuddyGPT.capabilities.http_request
Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any

@use_case("simple_web_api_documentation", "Minimal implementation of a web api documentation use case")
@dataclass
class SimpleWebAPIDocumentation(RoundBasedUseCase):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    # Description for expected HTTP methods
    http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.)."
    )

    # Template for HTTP methods in API requests
    http_method_template: str = parameter(
        desc="Template to format HTTP methods in API requests, with {method} replaced by actual HTTP method names.",
        default="{method}"
    )

    # List of expected HTTP methods
    http_methods: str = parameter(
        desc="Expected HTTP methods in the API, as a comma-separated list.",
        default="GET,POST,PUT,PATCH,DELETE"
    )

    def init(self):
        super().init()
        self._setup_capabilities()
        self._setup_initial_prompt()

        self.documentation_handler = DocumentationHandler(self.llm, self._capabilities)

    def _setup_initial_prompt(self):
        initial_prompt = {
            "role": "system",
            "content": f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                       f"Start with an empty OpenAPI specification.\n"
                       f"Maintain meticulousness in documenting your observations as you traverse the APIs."
        }
        self._prompt_history.append(initial_prompt)
        self.prompt_engineer = PromptEngineer(strategy=PromptStrategy.CHAIN_OF_THOUGHT, llm=self.llm, history=self._prompt_history, capabilities = self._capabilities)

    def _setup_capabilities(self):
        sett = {self.http_method_template.format(method=method) for method in self.http_methods.split(",")}
        notes = self._context["notes"]
        self._capabilities = {
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(notes)
        }

    def all_http_methods_found(self):
        self.console.print(Panel("All HTTP methods found! Congratulations!", title="system"))
        self._all_http_methods_found = True

    def perform_round(self, turn: int, FINAL_ROUND=30):
        prompt = self.prompt_engineer.generate_prompt(doc=True)
        #print(f'Prompt:{prompt}')
        tic = time.perf_counter()
        response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model, messages=prompt, response_model=capabilities_to_action_model(self._capabilities))
        toc = time.perf_counter()
        self._handle_response(completion, response, tic, toc)

    def _handle_response(self, completion, response, start_time, end_time):
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        command = pydantic_core.to_json(response).decode()
        self.console.print(Panel(command, title="assistant"))
        self._prompt_history.append(message)

        with self.console.status("[bold green]Executing that command..."):
            result = response.execute()
            self.console.print(Panel(result[:30], title="tool"))
            result_str = self.parse_http_status_line(result)
            self._prompt_history.append(tool_message(result_str, tool_call_id))
            print(f'result string:{result_str}')
            invalid_flags = ["recorded","Not a valid HTTP method" ]
            if not result_str in invalid_flags :
                self.documentation_handler.update_openapi_spec(response, result)
                self.documentation_handler.write_openapi_to_yaml()
        return self._all_http_methods_found

    def parse_http_status_line(self, status_line):
        if status_line == "Not a valid HTTP method":
            return status_line
        if status_line and " " in status_line:
            protocol, status_code, status_message = status_line.split(' ', 2)
            status_message = status_message.split("\r\n")[0]
            return f'{status_code} {status_message}'
        raise ValueError("Invalid HTTP status line")

    def has_no_numbers(self, path):
        return not any(char.isdigit() for char in path)

