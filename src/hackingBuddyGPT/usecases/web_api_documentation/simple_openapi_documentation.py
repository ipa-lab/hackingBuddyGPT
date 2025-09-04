import json
from logging import config
import os
from dataclasses import field

from rich.panel import Panel

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.base import AutonomousUseCase, use_case
from hackingBuddyGPT.usecases.web_api_documentation.openapi_specification_handler import \
    OpenAPISpecificationHandler
from hackingBuddyGPT.utils.capability_manager import CapabilityManager
from hackingBuddyGPT.utils.logging import Logger, log_param
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import PromptStrategy
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.prompt_engineer import PromptEngineer
from hackingBuddyGPT.utils.web_api.response_handler import ResponseHandler
from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler
from hackingBuddyGPT.utils.web_api.custom_datatypes import Context, Prompt
from hackingBuddyGPT.usecases.web_api_documentation.evaluator import Evaluator
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPIDocumentation(AutonomousUseCase):
    """
         SimpleWebAPIDocumentation is an agent class for automating REST API documentation.

        Attributes:
            llm (OpenAILib): The language model interface used for prompt execution.
            _prompt_history (Prompt): Internal history of prompts exchanged with the LLM.
            _context (Context): Context information used by capabilities (e.g., notes).
            config_path (str): Path to the configuration file for the API under test.
            strategy_string (str): Serialized string representing the documentation strategy to apply.
            _http_method_description (str): Description for identifying HTTP methods in responses.
            _http_method_template (str): Template string for formatting HTTP methods.
            _http_methods (str): Comma-separated list of expected HTTP methods.
            explore_steps_done (bool): Flag to indicate if exploration steps are completed.
            found_all_http_methods (bool): Flag indicating whether all HTTP methods have been found.
            all_steps_done (bool): Flag to indicate whether the full documentation process is complete.
        """
    llm: OpenAILib = None
    log: Logger = log_param
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: CapabilityManager = None
    _all_http_methods_found: bool = False
    config_path: str = parameter(
        desc="Configuration file path",
        default="",
    )

    strategy_string: str = parameter(
        desc="strategy string",
        default="",
    )

    prompt_file: str = parameter(
        desc="prompt file name",
        default="",
    )


    _http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).",
    )
    _http_method_template: str = parameter(
        desc="Template to format HTTP methods in API requests, with {method} replaced by actual HTTP method names.",
        default="{method}",
    )
    _http_methods: str = parameter(
        desc="Expected HTTP methods in the API, as a comma-separated list.",
        default="GET,POST,PUT,PATCH,DELETE",
    )

    def get_name(self) -> str:
        return self.__class__.__name__
    
    def get_strategy(self, strategy_string):

        strategies = {
            "cot": PromptStrategy.CHAIN_OF_THOUGHT,
            "tot": PromptStrategy.TREE_OF_THOUGHT,
            "icl": PromptStrategy.IN_CONTEXT
        }
        return strategies.get(strategy_string, PromptStrategy.IN_CONTEXT)

    def init(self):
        """Initialize the agent with configurations, capabilities, and handlers."""
        super().init()
        self.explore_steps_done = False
        self.found_all_http_methods = False
        self.all_steps_done = False

        # load config file
        self.strategy = self.get_strategy(self.strategy_string)

        """Loads JSON configuration from the specified path."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        with open(self.config_path, 'r') as file:
            config = json.load(file)
            token = config.get("token")
            self.host = config.get("host")
            description = config.get("description")
            self._correct_endpoints = config.get("correct_endpoints", {})
            query_params = config.get("query_params", {})

        self.categorized_endpoints = self.categorize_endpoints(self._correct_endpoints, query_params)

        # setup capabilities
        self._capabilities = CapabilityManager(self.log)
        self._capabilities.add_capability(HTTPRequest(self.host))
        self._capabilities.add_capability(RecordNote(self._context["notes"]))

        self._prompt_context = PromptContext.DOCUMENTATION
        name, initial_prompt = self._setup_initial_prompt(description=description)
        self._initialize_handlers(config=config, description=description, token=token, name=name,
                                  initial_prompt=initial_prompt)



    def _setup_initial_prompt(self, description: str):
        """
           Configures the initial prompt for the API documentation process.

           This prompt provides system-level instructions to the LLM, guiding it to start documenting
           the REST API from scratch using an empty OpenAPI specification.

           Args:
               description (str): A short description of the website or service being documented.

           Returns:
               tuple:
                   - str: The base project name, extracted from the config file name.
                   - dict: The initial prompt dictionary to be added to the prompt history.
           """
        initial_prompt = {
            "role": "system",
            "content": (
                f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                f"The website is {description}. Start with an empty OpenAPI specification and be meticulous in "
                f"documenting your observations as you traverse the APIs."
            ),
        }

        base_name = os.path.basename(self.config_path)

        # Split the base name by '_config' and take the first part
        name = base_name.split('_config')[0]

        self.prompt_helper = PromptGenerationHelper(self.host, description)
        return name, initial_prompt

    def _initialize_handlers(self, config, description, token, name, initial_prompt):
        """
           Initializes the core handler components required for API exploration and documentation.

           This includes setting up:
           - Capabilities such as HTTP request execution.
           - LLM interaction handler.
           - Response handling and OpenAPI documentation logic.
           - Prompt engineering strategy.
           - Evaluator for judging API test or doc performance.

           Args:
               config (dict): Configuration dictionary containing API setup options.
               description (str): Description of the target API or web service.
               token (str): Authorization token (if any) to be used for API interaction.
               name (str): Base name of the current documentation session.
               initial_prompt (dict): Initial system prompt for the LLM.
           """
        self.all_capabilities = {
                                 "http_request": HTTPRequest(self.host)}
        self._llm_handler = LLMHandler(self.llm, self._capabilities._capabilities,  all_possible_capabilities=self.all_capabilities)

        self._response_handler = ResponseHandler(llm_handler=self._llm_handler, prompt_context=self._prompt_context,
                                                 prompt_helper=self.prompt_helper, config=config)
        self._documentation_handler = OpenAPISpecificationHandler(
            self._llm_handler, self.strategy, self.host, description, name
        )

        self._prompt_history.append(initial_prompt)

        self._prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            context=PromptContext.DOCUMENTATION,
            prompt_helper=self.prompt_helper,
            open_api_spec=self._documentation_handler.openapi_spec,
            rest_api_info=(token, self.host, self._correct_endpoints, self.categorized_endpoints),
            prompt_file=self.prompt_file
        )
        self._evaluator = Evaluator(config=config)

    def categorize_endpoints(self, endpoints, query: dict):

        """
            Categorizes a list of API endpoints based on their path depth and structure.

            Endpoints are grouped into categories such as root-level, instance-level, subresources,
            and multi-level/related resources. Useful for prioritizing exploration and testing.

            Args:
                endpoints (list[str]): A list of API endpoint paths.
                query (dict): Dictionary of query parameters to associate with the categorized endpoints.

            Returns:
                dict: A dictionary containing categorized endpoint groups:
                    - "root_level": Endpoints like `/users`
                    - "instance_level": Endpoints with one ID parameter like `/users/{id}`
                    - "subresource": Direct subpaths without ID
                    - "related_resource": Nested resources with an ID in the middle like `/users/{id}/posts`
                    - "multi-level_resource": Deeper or complex nested resources
                    - "query": Query parameter values from the input
            """
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

    def all_http_methods_found(self, turn: int) -> bool:
        """
           Checks whether all expected HTTP methods (GET, POST, PUT, DELETE) have been discovered
           for each endpoint by the documentation engine.

           Args:
               turn (int): The current execution round or step index.

           Returns:
               bool: True if all methods are found and all exploration steps are complete, False otherwise.

           Side Effects:
               - Sets `self.found_all_http_methods` to True if conditions are met.
           """

        found_count = sum(len(endpoints) for endpoints in self._documentation_handler.endpoint_methods.values())
        expected_count = len(self._documentation_handler.endpoint_methods.keys()) * 4
        if found_count >= len(self._correct_endpoints) and self.all_steps_done:
            self.found_all_http_methods = True
        return self.found_all_http_methods

    def perform_round(self, turn: int) -> bool:
        """
           Executes a round of the API documentation loop based on the current turn number.

           The method selects between exploration and exploitation modes:
           - Turns 1–18: Run exploration (`_explore_mode`)
           - Turn 19: Switch to exploit mode until all endpoints are fully documented
           - Turn 20+: Resume exploration for completeness

           Args:
               turn (int): The current iteration index in the documentation process.

           Returns:
               bool: True if all HTTP methods have been discovered by the end of the round.
           """

        if turn <= 18:
            self._explore_mode(turn)
        elif turn <= 19:
            self._exploit_until_no_help_needed(turn)
        else:
            self._explore_mode(turn)

        return self.all_http_methods_found(turn)

    def _explore_mode(self, turn: int) -> None:
        """
         Executes the exploration phase for a documentation round.

         In this mode, the agent probes new API endpoints, extracts metadata,
         and updates its OpenAPI spec. The process continues until:
         - No new endpoints are discovered for several steps.
         - A maximum exploration depth is reached.
         - All HTTP methods are found.

         Args:
             turn (int): The current round number to be logged and used for prompt context.
         """

        last_endpoint_found_x_steps_ago, new_endpoint_count = 0, len(self._documentation_handler.endpoint_methods)
        last_found_endpoints = len(self._prompt_engineer.prompt_helper.found_endpoints)

        while (
                last_endpoint_found_x_steps_ago <= new_endpoint_count + 5
                and last_endpoint_found_x_steps_ago <= 10
                and not self.found_all_http_methods
        ):
            if self.explore_steps_done :
                self.run_documentation(turn, "exploit")
            else:
                self.run_documentation(turn, "explore")
            current_count = len(self._prompt_engineer.prompt_helper.found_endpoints)
            last_endpoint_found_x_steps_ago = last_endpoint_found_x_steps_ago + 1 if current_count == last_found_endpoints else 0
            last_found_endpoints = current_count
            if (updated_count := len(self._documentation_handler.endpoint_methods)) > new_endpoint_count:
                new_endpoint_count = updated_count
                self._prompt_engineer.open_api_spec = self._documentation_handler.openapi_spec

    def _exploit_until_no_help_needed(self, turn: int) -> None:
        """
           Repeatedly performs exploit mode to gather deeper documentation details
           for endpoints flagged as needing further clarification.

           This runs until all such endpoints are fully explained by the LLM agent.

           Args:
               turn (int): Current round number, passed to `run_documentation()` for tracking.

           """
        while self._prompt_engineer.prompt_helper.get_endpoints_needing_help():
            self.run_documentation(turn, "exploit")
            self._prompt_engineer.open_api_spec = self._documentation_handler.openapi_spec

    def _single_exploit_run(self, turn: int) -> None:
        """
           Performs a single exploit pass to extract more precise documentation
           for endpoints or parameters that may have been incompletely parsed.

           Args:
               turn (int): Current step number for context.

           """
        self.run_documentation(turn, "exploit")
        self._prompt_engineer.open_api_spec = self._documentation_handler.openapi_spec

    def has_no_numbers(self, path: str) -> bool:
        """
            Checks whether a given API path contains any numeric characters.

            This is useful for detecting generic vs. instance-level paths (e.g., `/users` vs. `/users/123`).

            Args:
                path (str): The API path to analyze.

            Returns:
                bool: True if the path contains no digits, False otherwise.
            """
        return not any(char.isdigit() for char in path)

    def run_documentation(self, turn: int, move_type: str) -> None:
        """
            Runs a full documentation interaction cycle with the LLM agent for the given turn and mode.

            This method forms the core of the documentation loop. It generates prompts, interacts with
            the LLM to simulate API calls, handles responses, updates the OpenAPI spec, and determines
            when to advance exploration or exploitation steps based on multiple heuristics.

            Args:
                turn (int): The current turn index (used for context and state progression).
                move_type (str): Either `"explore"` or `"exploit"`, determining the type of documentation logic used.

            """
        is_good = False
        counter = 0
        while not is_good:
            prompt = self._prompt_engineer.generate_prompt(turn=turn, move_type=move_type,
                                                           prompt_history=self._prompt_history)
            response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt,"http_request" )
            self.log.console.print(Panel(prompt[-1]["content"], title="system"))

            is_good, self._prompt_history, result, result_str = self._response_handler.handle_response(response,
                                                                                                       completion,
                                                                                                       self._prompt_history,
                                                                                                       self.log,
                                                                                                       self.categorized_endpoints,
                                                                                                       move_type)

            if result == None or "Could not request" in result:
                continue
            self._prompt_history, self._prompt_engineer = self._documentation_handler.document_response(
                result, response, result_str, self._prompt_history, self._prompt_engineer
            )
            self.prompt_helper.endpoint_examples = self._documentation_handler.endpoint_examples

            if self._prompt_engineer.prompt_helper.current_step == 7 and move_type == "explore":
                is_good = True
                self.prompt_helper.current_step += 1
                self._response_handler.query_counter = 0
            if self._prompt_engineer.prompt_helper.current_step == 2 and len(self.prompt_helper._get_instance_level_endpoints("")) ==0:
                is_good = True
                self.prompt_helper.current_step += 1
                self._response_handler.query_counter = 0


            if self._response_handler.query_counter == 600 and self.prompt_helper.current_step == 6:
                is_good = True
                self.explore_steps_done = True
                self.prompt_helper.current_step += 1
                self._response_handler.query_counter = 0

            if  move_type == "exploit" :
                if self._response_handler.query_counter >= 50 :
                    is_good = True
                    self.all_steps_done = True

            if self._prompt_engineer.prompt_helper.current_step < 6 and self._response_handler.no_new_endpoint_counter >30:
                is_good = True
                self._response_handler.no_new_endpoint_counter = 0
                self.prompt_helper.current_step += 1
                self._response_handler.query_counter = 0

            if self._prompt_engineer.prompt_helper.current_step < 6 and self._response_handler.query_counter > 200:
                is_good = True
                self.prompt_helper.current_step += 1
                self._response_handler.query_counter = 0

            counter = counter + 1
            self.prompt_helper.found_endpoints = list(set(self._prompt_engineer.prompt_helper.found_endpoints))

            self._evaluator.evaluate_response(response, self._prompt_engineer.prompt_helper.found_endpoints, self.prompt_helper.current_step,
                                              self.prompt_helper.found_query_endpoints)

            self._evaluator.finalize_documentation_metrics(
                file_path=self._documentation_handler.file.split(".yaml")[0] + ".txt")

        self.all_http_methods_found(turn)