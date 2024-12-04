import json
import os.path
from dataclasses import field
from datetime import datetime
from typing import Any, Dict, List

import pydantic_core
from rich.panel import Panel

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.pased_information import ParsedInformation
from hackingBuddyGPT.capabilities.python_test_case import PythonTestCase
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptContext, \
    PromptPurpose
from hackingBuddyGPT.usecases.web_api_testing.documentation.parsing import OpenAPISpecificationParser
from hackingBuddyGPT.usecases.web_api_testing.documentation.report_handler import ReportHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptContext
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer_with_llm import \
    ResponseAnalyzerWithLLM
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.testing.test_handler import TestHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Context, Prompt
from hackingBuddyGPT.usecases.web_api_testing.utils.llm_handler import LLMHandler
from hackingBuddyGPT.utils import tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


# OpenAPI specification file path


class SimpleWebAPITesting(Agent):
    """
    SimpleWebAPITesting is an agent class for automating web API testing.

    Attributes:
        llm (OpenAILib): The language model interface for generating prompts and handling responses.
        host (str): The host URL to test.
        http_method_description (str): Description pattern for expected HTTP methods in the API response.
        http_method_template (str): Template for formatting HTTP methods in API requests.
        http_methods (str): Comma-separated list of HTTP methods expected in the API response.
        _prompt_history (Prompt): The history of prompts sent to the language model.
        _context (Context): Contextual data for the test session.
        _capabilities (Dict[str, Capability]): Available capabilities for the agent.
        _all_http_methods_found (bool): Flag indicating if all HTTP methods have been found.
    """

    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).",
    )
    http_method_template: str = parameter(
        desc="Template used to format HTTP methods in API requests. The {method} placeholder will be replaced by actual HTTP method names.",
        default="{method}",
    )
    http_methods: str = parameter(
        desc="Comma-separated list of HTTP methods expected to be used in the API response.",
        default="GET,POST,PUT,DELETE",
    )
    config_path: str = parameter(
        desc="Configuration file path",
        default="",
    )

    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list(), "test_cases": list(), "parsed":list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    def init(self):
        super().init()
        self._setup_config_path()
        self.config = self._load_config()
        self._extract_config_values(self.config)
        self._set_strategy()
        self._load_openapi_specification()
        self._setup_environment()
        self._setup_handlers()
        self._setup_initial_prompt()

    def _setup_config_path(self):
        if self.config_path:
            current_file_path = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(current_file_path, "configs", self.config_path)

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        with open(self.config_path, 'r') as file:
            return json.load(file)

    def _extract_config_values(self, config):
        self.token = config.get("token")
        self.host = config.get("host")
        self.description = config.get("description")
        self.correct_endpoints = config.get("correct_endpoints", {})
        self.query_params = config.get("query_params", {})

    def _set_strategy(self):
        strategies = {
            "cot": PromptStrategy.CHAIN_OF_THOUGHT,
            "tot": PromptStrategy.TREE_OF_THOUGHT,
            "icl": PromptStrategy.IN_CONTEXT
        }
        self.strategy = strategies.get(self.strategy, PromptStrategy.IN_CONTEXT)

    def _load_openapi_specification(self):
        if os.path.exists(self.config_path):
            self._openapi_specification_parser = OpenAPISpecificationParser(self.config_path)
            self._openapi_specification = self._openapi_specification_parser.api_data

    def _setup_environment(self):
        self._context["host"] = self.host
        self._setup_capabilities()
        self.categorized_endpoints = self.categorize_endpoints(self.correct_endpoints, self.query_params)
        self.prompt_context = PromptContext.PENTESTING

    def _setup_handlers(self):
        self._llm_handler = LLMHandler(self.llm, self._capabilities)
        self.prompt_helper = PromptGenerationHelper(host=self.host)
        self.pentesting_information = PenTestingInformation(self._openapi_specification_parser)
        self._response_handler = ResponseHandler(
            llm_handler=self._llm_handler, prompt_context=self.prompt_context, prompt_helper=self.prompt_helper,
            config=self.config, pentesting_information = self.pentesting_information)
        self.response_analyzer = ResponseAnalyzerWithLLM(llm_handler=self._llm_handler,
                                                         pentesting_info=self.pentesting_information,
                                                         capacity=self.parse_capacity)
        self._response_handler.response_analyzer = self.response_analyzer
        self._report_handler = ReportHandler()
        self._test_handler = TestHandler(self._llm_handler, self.python_test_case_capability)

    def categorize_endpoints(self, endpoints, query: dict):
        root_level = []
        single_parameter = []
        subresource = []
        related_resource = []
        multi_level_resource = []

        for endpoint in endpoints:
            # Split the endpoint by '/' and filter out empty strings
            parts = [part for part in endpoint.split('/') if part]

            # Determine the category based on the structure
            if len(parts) == 1:
                root_level.append(endpoint)
            elif len(parts) == 2:
                if "id" in endpoint:
                    single_parameter.append(endpoint)
                else:
                    subresource.append(endpoint)
            elif len(parts) == 3:
                if "id" in endpoint:
                    related_resource.append(endpoint)
                else:
                    multi_level_resource.append(endpoint)
            else:
                multi_level_resource.append(endpoint)

        return {
            "root_level": root_level,
            "instance_level": single_parameter,
            "subresource": subresource,
            "query": query.values(),
            "related_resource": related_resource,
            "multi-level_resource": multi_level_resource,
        }

    def _setup_initial_prompt(self) -> None:
        """
        Sets up the initial prompt for the LLM. The prompt provides instructions for the LLM
        to evaluate the REST APIs of the specified host and to document findings.
        """
        initial_prompt: Dict[str, str] = {
            "role": "system",
            "content": (
                f"You're a seasoned API tester tasked with evaluating the REST APIs of a website hosted at {self.host}. "
                f"Your primary objective is to thoroughly explore the APIs, understanding their endpoints, parameters, and responses, "
                f"and then devise and execute potential exploits. Be diligent in documenting your findings as you navigate through the APIs. "
                f"Avoid resorting to brute-force tactics. All necessary information can be obtained from the API endpoints themselves. "
                f"Remember, if you encounter an HTTP method ({self.http_method_description}), promptly submit it as it is of utmost importance."
            ),
        }
        self._prompt_history.append(initial_prompt)
        handlers = (self._llm_handler, self._response_handler)
        schemas: Dict[str, Any] = {}
        endpoints: Dict[str, Any] = self.correct_endpoints

        self.prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            history=self._prompt_history,
            handlers=(self._llm_handler, self._response_handler),
            context=PromptContext.PENTESTING,
            open_api_spec=self._openapi_specification,
            rest_api_info=(self.token, self.description, self.correct_endpoints, self.categorized_endpoints),
            prompt_helper=self.prompt_helper
        )
        self.prompt_engineer.set_pentesting_information(self.pentesting_information)
        self.purpose = PromptPurpose.AUTHENTICATION

    def all_http_methods_found(self) -> None:
        """
        Handles the event when all HTTP methods are found. Displays a congratulatory message
        and sets the _all_http_methods_found flag to True.
        """
        self._log.console.print(Panel("All HTTP methods found! Congratulations!", title="system"))
        self._all_http_methods_found = True

    def _setup_capabilities(self) -> None:
        """
        Sets up the capabilities required for the use case. Initializes HTTP request capabilities,
        note recording capabilities, and HTTP method submission capabilities based on the provided
        configuration.
        """
        methods_set: set[str] = {
            self.http_method_template.format(method=method) for method in self.http_methods.split(",")
        }
        notes: List[str] = self._context["notes"]
        parsed: List[str] = self._context["parsed"]
        test_cases = self._context["test_cases"]
        self.python_test_case_capability = {"python_test_case": PythonTestCase(test_cases)}
        self.parse_capacity = {"parse": ParsedInformation(test_cases)}
        self._capabilities = {
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(notes)
        }
        self.http_capability = {            "http_request": HTTPRequest(self.host),
}

    def perform_round(self, turn: int) -> None:
        """
        Performs a single round of interaction with the LLM. Generates a prompt, sends it to the LLM,
        and handles the response.

        Args:
            turn (int): The current round number.
        """
        self._perform_prompt_generation(turn)
        if turn == 20:
            self._report_handler.save_report()

    def _perform_prompt_generation(self, turn: int) -> None:
        response: Any
        completion: Any
        while self.purpose == self.prompt_engineer.purpose:
            prompt = self.prompt_engineer.generate_prompt(turn=turn, move_type="explore", log=self._log,
                                                          prompt_history=self._prompt_history,
                                                          llm_handler=self._llm_handler)
            response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt,self.http_capability )
            self._handle_response(completion, response, self.prompt_engineer.purpose)

        self.purpose = self.prompt_engineer.purpose
        if self.purpose == PromptPurpose.LOGGING_MONITORING:
            self.pentesting_information.next_testing_endpoint()

    def _handle_response(self, completion: Any, response: Any, purpose: str) -> None:
        """
        Handles the response from the LLM. Parses the response, executes the necessary actions,
        and updates the prompt history.

        Args:
            completion (Any): The completion object from the LLM.
            response (Any): The response object from the LLM.
            purpose (str): The purpose or intent behind the response handling.
        """
        message = completion.choices[0].message
        tool_call_id: str = message.tool_calls[0].id
        command: str = pydantic_core.to_json(response).decode()
        self._log.console.print(Panel(command, title="assistant"))
        self._prompt_history.append(message)

        with self._log.console.status("[bold green]Executing that command..."):
            result: Any = response.execute()
            self._log.console.print(Panel(result[:30], title="tool"))
            if not isinstance(result, str):
                endpoint: str = str(response.action.path).split("/")[1]
                self._report_handler.write_endpoint_to_report(endpoint)

            self._prompt_history.append(
                tool_message(self._response_handler.extract_key_elements_of_response(result), tool_call_id))

            analysis, status_code = self._response_handler.evaluate_result(result=result, prompt_history=self._prompt_history, analysis_context= self.prompt_helper.purpose)
            self._prompt_history = self._test_handler.generate_test_cases(analysis=analysis, endpoint=response.action.path,
                                                   method=response.action.method,
                                                   prompt_history=self._prompt_history, status_code=status_code)
            self._report_handler.write_analysis_to_report(analysis=analysis, purpose=self.prompt_engineer.purpose)

        self.all_http_methods_found()



@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPITestingUseCase(AutonomousAgentUseCase[SimpleWebAPITesting]):
    """
    A use case for the SimpleWebAPITesting agent, encapsulating the setup and execution
    of the web API testing scenario.
    """

    pass
