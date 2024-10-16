from dataclasses import field
from typing import Dict

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.web_api_testing.documentation.openapi_specification_handler import (
    OpenAPISpecificationHandler,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptContext
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Context, Prompt
from hackingBuddyGPT.usecases.web_api_testing.utils.llm_handler import LLMHandler
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


class SimpleWebAPIDocumentation(Agent):
    """
    SimpleWebAPIDocumentation is an agent that documents REST APIs of a website by interacting with the APIs and
    generating an OpenAPI specification.

    Attributes:
        llm (OpenAILib): The language model to use for interaction.
        host (str): The host URL of the website to test.
        _prompt_history (Prompt): The history of prompts and responses.
        _context (Context): The context containing notes.
        _capabilities (Dict[str, Capability]): The capabilities of the agent.
        _all_http_methods_found (bool): Flag indicating if all HTTP methods were found.
        _http_method_description (str): Description for expected HTTP methods.
        _http_method_template (str): Template to format HTTP methods in API requests.
        _http_methods (str): Expected HTTP methods in the API.
    """

    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    # Description for expected HTTP methods
    _http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).",
    )

    # Template for HTTP methods in API requests
    _http_method_template: str = parameter(
        desc="Template to format HTTP methods in API requests, with {method} replaced by actual HTTP method names.",
        default="{method}",
    )

    # List of expected HTTP methods
    _http_methods: str = parameter(
        desc="Expected HTTP methods in the API, as a comma-separated list.",
        default="GET,POST,PUT,PATCH,DELETE",
    )

    def init(self):
        """Initializes the agent with its capabilities and handlers."""
        super().init()
        self.found_all_http_methods: bool = False
        self._setup_capabilities()
        self.llm_handler = LLMHandler(self.llm, self._capabilities)
        self.response_handler = ResponseHandler(self.llm_handler)
        self.strategy = PromptStrategy.IN_CONTEXT
        self.documentation_handler = OpenAPISpecificationHandler(self.llm_handler, self.response_handler, self.strategy)
        self._setup_initial_prompt()

    def _setup_capabilities(self):
        """Sets up the capabilities for the agent."""
        notes = self._context["notes"]
        self._capabilities = {"http_request": HTTPRequest(self.host), "record_note": RecordNote(notes)}

    def _setup_initial_prompt(self):
        """Sets up the initial prompt for the agent."""
        initial_prompt = {
            "role": "system",
            "content": f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                       f"Start with an empty OpenAPI specification.\n"
                       f"Maintain meticulousness in documenting your observations as you traverse the APIs.",
        }
        self._prompt_history.append(initial_prompt)
        handlers = (self.llm_handler, self.response_handler)
        self.prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            history=self._prompt_history,
            handlers=handlers,
            context=PromptContext.DOCUMENTATION,
            open_api_spec=self.documentation_handler.openapi_spec
        )

    def all_http_methods_found(self, turn):
        """
        Checks if all expected HTTP methods have been found.

        Args:
            turn (int): The current turn number.

        Returns:
            bool: True if all HTTP methods are found, False otherwise.
        """
        found_endpoints = sum(len(value_list) for value_list in self.documentation_handler.endpoint_methods.values())
        expected_endpoints = len(self.documentation_handler.endpoint_methods.keys()) * 4
        print(f"found methods:{found_endpoints}")
        print(f"expected methods:{expected_endpoints}")
        if (
                found_endpoints > 0
                and (found_endpoints == expected_endpoints)
                or turn == 20
                and found_endpoints > 0
                and (found_endpoints == expected_endpoints)
        ):
            self.found_all_http_methods = True
            return self.found_all_http_methods
        return self.found_all_http_methods

    def perform_round(self, turn: int) -> bool:
        """
        Performs a round of API documentation.

        Args:
            turn (int): The current turn number.

        Returns:
            bool: True if all HTTP methods are found, False otherwise.
        """
        if turn == 1:
            last_endpoint_found_x_steps_ago = 0
            new_endpoint_count = len(self.documentation_handler.endpoint_methods)
            last_number_of_found_endpoints = 0
            while (last_endpoint_found_x_steps_ago <= new_endpoint_count + 2
                   and last_endpoint_found_x_steps_ago <= 5
                   and not self.found_all_http_methods):
                self.run_documentation(turn, "explore")

                # Check if new endpoints have been found
                current_endpoint_count = len(self.prompt_engineer.prompt_helper.found_endpoints)
                if last_number_of_found_endpoints == len(self.prompt_engineer.prompt_helper.found_endpoints):
                    last_endpoint_found_x_steps_ago += 1
                else:
                    last_endpoint_found_x_steps_ago = 0  # Reset if a new endpoint is found

                # Update if new endpoint methods are discovered
                if len(self.documentation_handler.endpoint_methods) > new_endpoint_count:
                    new_endpoint_count = len(self.documentation_handler.endpoint_methods)
                    self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec

                last_number_of_found_endpoints = current_endpoint_count

        elif turn == 20:
            # Continue until all endpoints needing help are addressed
            while self.prompt_engineer.prompt_helper.get_endpoints_needing_help():
                self.run_documentation(turn, "exploit")
                self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec
        else:
            # For other turns, run documentation in exploit mode
            self.run_documentation(turn, "exploit")
            self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec

        return self.all_http_methods_found(turn)

    def has_no_numbers(self, path):
        """
        Checks if the path contains no numbers.

        Args:
            path (str): The path to check.

        Returns:
            bool: True if the path contains no numbers, False otherwise.
        """
        return not any(char.isdigit() for char in path)

    def run_documentation(self, turn, move_type):
        """
        Runs the documentation process for a given turn and move type.

        Args:
            turn (int): The current turn number.
            move_type (str): The move type ('explore' or 'exploit').
        """
        prompt = self.prompt_engineer.generate_prompt(turn, move_type)
        response, completion = self.llm_handler.call_llm(prompt)
        self._log, self._prompt_history, self.prompt_engineer = self.documentation_handler.document_response(
            completion, response, self._log, self._prompt_history, self.prompt_engineer
        )
        self.all_http_methods_found(turn)


@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPIDocumentationUseCase(AutonomousAgentUseCase[SimpleWebAPIDocumentation]):
    """Use case for the SimpleWebAPIDocumentation agent."""

    pass
