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
        self._setup_capabilities()
        self.llm_handler = LLMHandler(self.llm, self._capabilities)
        self.response_handler = ResponseHandler(self.llm_handler)
        self._setup_initial_prompt()
        self.documentation_handler = OpenAPISpecificationHandler(self.llm_handler, self.response_handler)

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
            strategy=PromptStrategy.CHAIN_OF_THOUGHT,
            history=self._prompt_history,
            handlers=handlers,
            context=PromptContext.DOCUMENTATION,
            rest_api=self.host,
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
            return True
        return False

    def perform_round(self, turn: int):
        """
        Performs a round of API documentation.

        Args:
            turn (int): The current turn number.

        Returns:
            bool: True if all HTTP methods are found, False otherwise.
        """
        if turn == 1:
            counter = 0
            new_endpoint_found = 0
            while counter <= new_endpoint_found + 2 and counter <= 10:
                self.run_documentation(turn, "explore")
                counter += 1
                if len(self.documentation_handler.endpoint_methods) > new_endpoint_found:
                    new_endpoint_found = len(self.documentation_handler.endpoint_methods)
        elif turn == 20:
            while len(self.prompt_engineer.prompt_helper.get_endpoints_needing_help()) != 0:
                self.run_documentation(turn, "exploit")
        else:
            self.run_documentation(turn, "exploit")
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
        self.log, self._prompt_history, self.prompt_engineer = self.documentation_handler.document_response(
            completion, response, self.log, self._prompt_history, self.prompt_engineer
        )


@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPIDocumentationUseCase(AutonomousAgentUseCase[SimpleWebAPIDocumentation]):
    """Use case for the SimpleWebAPIDocumentation agent."""

    pass
