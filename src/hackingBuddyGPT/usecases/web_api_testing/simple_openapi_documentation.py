from dataclasses import field
from typing import List, Any, Union, Dict

import pydantic_core
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from rich.panel import Panel

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.web_api_testing.utils.openapi_specification_manager import OpenAPISpecificationManager
from hackingBuddyGPT.usecases.web_api_testing.utils.llm_handler import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.utils.response_handler import ResponseHandler
from hackingBuddyGPT.utils import tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any

class SimpleWebAPIDocumentation(Agent):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    # Description for expected HTTP methods
    _http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.)."
    )

    # Template for HTTP methods in API requests
    _http_method_template: str = parameter(
        desc="Template to format HTTP methods in API requests, with {method} replaced by actual HTTP method names.",
        default="{method}"
    )

    # List of expected HTTP methods
    _http_methods: str = parameter(
        desc="Expected HTTP methods in the API, as a comma-separated list.",
        default="GET,POST,PUT,PATCH,DELETE"
    )

    def init(self):
        super().init()
        self._setup_capabilities()
        self.llm_handler = LLMHandler(self.llm, self._capabilities)
        self.response_handler = ResponseHandler(self.llm_handler)
        self._setup_initial_prompt()
        self.documentation_handler = OpenAPISpecificationManager(self.llm_handler, self.response_handler)

    def _setup_capabilities(self):
        notes = self._context["notes"]
        self._capabilities = {
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(notes)
        }

    def _setup_initial_prompt(self):
        initial_prompt = {
            "role": "system",
            "content": f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                       f"Start with an empty OpenAPI specification.\n"
                       f"Maintain meticulousness in documenting your observations as you traverse the APIs."
        }
        self._prompt_history.append(initial_prompt)
        self.prompt_engineer = PromptEngineer(strategy=PromptStrategy.CHAIN_OF_THOUGHT, llm_handler=self.llm_handler,
                                              history=self._prompt_history, schemas={},
                                              response_handler=self.response_handler)


    def all_http_methods_found(self):
        print(f'found endpoints:{self.documentation_handler.endpoint_methods.items()}')
        print(f'found endpoints values:{self.documentation_handler.endpoint_methods.values()}')

        found_endpoints = sum(len(value_list) for value_list in self.documentation_handler.endpoint_methods.values())
        expected_endpoints = len(self.documentation_handler.endpoint_methods.keys())*4
        print(f'found endpoints:{found_endpoints}')
        print(f'expected endpoints:{expected_endpoints}')
        print(f'correct? {found_endpoints== expected_endpoints}')
        if found_endpoints== expected_endpoints or found_endpoints == expected_endpoints -1:
            return True
        else:
            return False

    def perform_round(self, turn: int):
        prompt = self.prompt_engineer.generate_prompt(doc=True)
        response, completion = self.llm_handler.call_llm(prompt)
        return self._handle_response(completion, response)

    def _handle_response(self, completion, response):
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        command = pydantic_core.to_json(response).decode()
        self._log.console.print(Panel(command, title="assistant"))
        self._prompt_history.append(message)

        with self._log.console.status("[bold green]Executing that command..."):
            result = response.execute()
            self._log.console.print(Panel(result[:30], title="tool"))
            result_str = self.response_handler.parse_http_status_line(result)
            self._prompt_history.append(tool_message(result_str, tool_call_id))
            invalid_flags = ["recorded","Not a valid HTTP method", "404" ,"Client Error: Not Found"]
            print(f'result_str:{result_str}')
            if not result_str in invalid_flags  or any(item in result_str for item in invalid_flags):
                self.prompt_engineer.found_endpoints = self.documentation_handler.update_openapi_spec(response, result)
                self.documentation_handler.write_openapi_to_yaml()
                self.prompt_engineer.schemas = self.documentation_handler.schemas
                from collections import defaultdict
                http_methods_dict = defaultdict(list)

                # Iterate through the original dictionary
                for endpoint, methods in self.documentation_handler.endpoint_methods.items():
                    for method in methods:
                        http_methods_dict[method].append(endpoint)
                self.prompt_engineer.endpoint_found_methods =  http_methods_dict
                self.prompt_engineer.endpoint_methods = self.documentation_handler.endpoint_methods
                print(f'SCHEMAS:{self.prompt_engineer.schemas}')
        return self.all_http_methods_found()



    def has_no_numbers(self, path):
        return not any(char.isdigit() for char in path)


@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPIDocumentationUseCase(AutonomousAgentUseCase[SimpleWebAPIDocumentation]):
    pass