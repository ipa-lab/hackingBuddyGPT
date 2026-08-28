import json
import os.path
from dataclasses import dataclass, field
from typing import Any, Dict, List

from rich.panel import Panel

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.capabilities.parsed_information import ParsedInformation
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.strategies import SimpleStrategy
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import strategy_from_string
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose
from hackingBuddyGPT.utils.openapi.openapi_parser import OpenAPISpecificationParser
from hackingBuddyGPT.usecases.web_api.report_handler import ReportHandler
from hackingBuddyGPT.usecases.web_api.proposed_http_request import ProposedHTTPRequest
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.prompt_engineer import PromptEngineer
from hackingBuddyGPT.utils.web_api.response_analyzer_with_llm import \
    ResponseAnalyzerWithLLM
from hackingBuddyGPT.utils.web_api.response_handler import ResponseHandler
from hackingBuddyGPT.utils.web_api.custom_datatypes import Context, Prompt
from hackingBuddyGPT.utils import tool_message
from hackingBuddyGPT.utils.configurable import parameter


# OpenAPI specification file path

# NOTE: This class is no longer a standalone CLI use case; it is the *testing phase engine*
# driven by the merged `WebAPITesting` use case (see usecases/web_api/web_api_testing.py).
# It stays a constructible dataclass so its unit tests and the orchestrator can build it, and
# so it can consume any TargetSurface (a passed-in OpenAPI spec, a sitemap, or a spec produced
# by the detection phase) instead of only loading one from the config's oas/ sibling file.
@dataclass
class SimpleWebAPITesting(SimpleStrategy):
    """
    SimpleWebAPITesting is an agent class for automating web API testing.

    Attributes:
        llm (LiteLLM): The language model interface for generating prompts and handling responses.
        host (str): The host URL to test.
        http_method_description (str): Description pattern for expected HTTP methods in the API response.
        http_method_template (str): Template for formatting HTTP methods in API requests.
        http_methods (str): Comma-separated list of HTTP methods expected in the API response.
        _prompt_history (Prompt): The history of prompts sent to the language model.
        _context (Context): Contextual data for the test session.
        _capabilities (Dict[str, Capability]): Available capabilities for the agent.
        _all_test_cases_run (bool): Flag indicating if all HTTP methods have been found.
    """

    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    config_path: str = parameter(
        desc="Configuration file path",
        default="",
    )

    strategy_string: str = parameter(
        desc="strategy string",
        default="",
    )

    _http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).",
    )
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list(), "test_cases": list(), "parsed": list()})
    _all_test_cases_run: bool = False

    def init(self):
        super().init()

        # Run limits (tokens/cost/duration/rounds). The orchestrator injects a shared Limits before
        # init(); a never-reached default keeps this engine usable stand-alone / in tests.
        if self.limits is None:
            self.limits = Limits(max_rounds=0, max_tokens=0, max_cost=0, max_duration=0)

        # load config file
        self.strategy = strategy_from_string(self.strategy_string)

        """Loads JSON configuration from the specified path."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        with open(self.config_path, 'r') as file:
            self.config = json.load(file)
            self.token = self.config.get("token")
            self.host = self.config.get("host")
            self.description = self.config.get("description")
            self.correct_endpoints = self.config.get("correct_endpoints", {})
            self.query_params = self.config.get("query_params", {})

        self._load_openapi_specification()
        self._setup_environment()
        self._setup_handlers()
        self._setup_initial_prompt()
        self.last_prompt = ""

    def get_name(self) -> str:
        return self.__class__.__name__

    def _load_openapi_specification(self):
        """
           Resolves the target surface the pentest runs against.

           If a surface was injected (``self._injected_surface`` — an OpenAPI spec, a sitemap, or
           a spec produced by the detection phase), it is used directly. Otherwise the OpenAPI
           spec is loaded from the config's sibling ``oas/<name>_oas.json`` as before.
           """
        injected = getattr(self, "_injected_surface", None)
        if injected is not None:
            self._openapi_specification_parser = injected
            self._openapi_specification = injected.api_data
        elif os.path.exists(self.config_path):
            self._openapi_specification_parser = OpenAPISpecificationParser(self.config_path)
            self._openapi_specification = self._openapi_specification_parser.api_data

    def _setup_environment(self):
        """
           Initializes core environment context for API testing or exploration.

           This includes:
           - Setting the target host.
           - Configuring capabilities.
           - Categorizing endpoints based on relevance and available query parameters.
           - Setting the prompt context to `PromptContext.PENTESTING`.
           """
        self._context["host"] = self.host

        # setup capabilities
        self._capabilities.add_capability(HTTPRequest(self.host))

        self._setup_capabilities()
        self.categorized_endpoints = self._openapi_specification_parser.categorize_endpoints(self.correct_endpoints,
                                                                                             self.query_params)
        self.prompt_context = PromptContext.PENTESTING

    def _setup_handlers(self):
        """
            Sets up all core internal components and handlers required for API testing.

            This includes:
            - LLM handler for prompt execution and capability routing.
            - Prompt helper for managing request state and prompt logic.
            - Pentesting information tracker to hold user/resource data and API config.
            - Response handler for parsing and reacting to tool responses.
            - Response analyzer powered by LLMs for deeper inspection.
            - Reporting handler to track and export findings.

            If username and password are not found in the config, defaults are used.
            """
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)
        if "username" in self.config.keys() and "password" in self.config.keys():
            username = self.config.get("username")
            password = self.config.get("password")
        else:
            username = "test"
            password = "<PASSWORD>"
        self.pentesting_information = PenTestingInformation(self._openapi_specification_parser, self.config)
        # The capability the model is given for the testing round: it finalises the proposed request
        # against the current test step and sends it (see ProposedHTTPRequest). Registered in the
        # CapabilityManager so the standard run_capability_json path can execute it.
        self._proposed_http_request = ProposedHTTPRequest(
            http_request=HTTPRequest(self.host),
            prompt_helper=self.prompt_helper,
            pentesting_information=self.pentesting_information,
        )
        self._capabilities.add_capability(self._proposed_http_request, name="ProposedHTTPRequest")
        self._response_handler = ResponseHandler(
            prompt_context=self.prompt_context, prompt_helper=self.prompt_helper,
            config=self.config, pentesting_information=self.pentesting_information)
        self.response_analyzer = ResponseAnalyzerWithLLM(llm=self.llm,
                                                         capabilities=self.all_capabilities,
                                                         pentesting_info=self.pentesting_information,
                                                         capacity=self.parse_capacity,
                                                         prompt_helper=self.prompt_helper,
                                                         limits=self.limits)
        self._response_handler.set_response_analyzer(self.response_analyzer)
        self._report_handler = ReportHandler(self.config)

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
                f"Remember, if you encounter an HTTP method ({self._http_method_description}), promptly submit it as it is of utmost importance."
            ),
        }
        self._prompt_history.append(initial_prompt)

        self.prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            context=PromptContext.PENTESTING,
            open_api_spec=self._openapi_specification,
            rest_api_info=(self.token, self.description, self.correct_endpoints, self.categorized_endpoints),
            prompt_helper=self.prompt_helper
        )
        self.prompt_engineer.set_pentesting_information(self.pentesting_information)
        self.purpose = self.pentesting_information.pentesting_step_list[0]

    def all_test_cases_run(self) -> None:
        """
        Handles the event when all HTTP methods are found. Displays a congratulatory message
        and sets the _all_http_methods_found flag to True.
        """
        self.log.console.print(Panel("All test cases run!", title="system"))
        self._all_test_cases_run = True

    def _setup_capabilities(self) -> None:
        """
        Sets up the capabilities required for the use case. Initializes HTTP request capabilities,
        note recording capabilities, and HTTP method submission capabilities based on the provided
        configuration.
        """
        notes: List[str] = self._context["notes"]
        parsed: List[str] = self._context["parsed"]
        test_cases = self._context["test_cases"]
        self.parse_capacity = {"parse": ParsedInformation(test_cases)}
        self.all_capabilities = {"parse": ParsedInformation(test_cases),
                                 "http_request": HTTPRequest(self.host),
                                 "record_note": RecordNote(notes)}
        self.http_capability = {"http_request": HTTPRequest(self.host),
                                }

    async def perform_round(self, turn: int) -> None:
        """
        Performs a single round of interaction with the LLM. Generates a prompt, sends it to the LLM,
        and handles the response.

        Args:
            turn (int): The current round number.
        """
        await self._perform_prompt_generation(turn)
        if len(self.prompt_engineer.pentesting_information.pentesting_step_list) == 0:
            self.all_test_cases_run()
            return
        if turn == 20:
            self._report_handler.save_report()

    async def _perform_prompt_generation(self, turn: int) -> None:
        while self.purpose == self.prompt_engineer._purpose and not self._all_test_cases_run and not self.limits.reached():
            prompt = self.prompt_engineer.generate_prompt(turn=turn, move_type="explore",
                                                          prompt_history=self._prompt_history)

            await self._run_testing_step(prompt)
            if len(self.prompt_engineer.pentesting_information.pentesting_step_list) == 0:
                self.all_test_cases_run()
                return

        self.purpose = self.prompt_engineer._purpose


    async def _run_testing_step(self, prompt) -> None:
        """Run one testing round on the standard LLM loop.

        The model is offered exactly one capability (``ProposedHTTPRequest``) and forced to call it
        (``tool_choice="required"``). The capability finalises and sends the request and captures
        response state; here we record the LLM result (cost/tokens via ``call_response``), execute the
        tool call through the shared ``run_capability_json`` path (structured ``add_tool_call``
        logging), and drive reporting + LLM analysis exactly as before.
        """
        llm_result = self.llm.get_response(
            prompt,
            capabilities={"ProposedHTTPRequest": self._proposed_http_request},
            tool_choice="required",
        )
        self.limits.register_message(llm_result)
        message_id = await self.log.call_response(llm_result)

        message = llm_result.result
        self._prompt_history.append(message)
        if not getattr(message, "tool_calls", None):
            return

        # Execute sequentially: the capability mutates shared prompt_helper/account state, which is not
        # safe to run concurrently. tool_choice="required" over a single capability yields one call.
        for tool_call in message.tool_calls:
            result = await self._capabilities.run_capability_json(
                message_id, tool_call.id, tool_call.function.name, tool_call.function.arguments
            )
            self._prompt_history.append(
                tool_message(self._response_handler.extract_key_elements_of_response(result), tool_call.id)
            )

            self._report_handler.write_vulnerability_to_report(
                self.prompt_helper.current_sub_step, self.prompt_helper.current_test_step, result,
                self.prompt_helper.counter)

            analysis, status_code = await self._response_handler.evaluate_result(
                result=result,
                prompt_history=self._prompt_history,
                analysis_context=self.prompt_engineer.prompt_helper.current_test_step)

            if self.purpose != PromptPurpose.SETUP:
                self._report_handler.write_analysis_to_report(analysis=analysis, purpose=self.prompt_engineer._purpose)
