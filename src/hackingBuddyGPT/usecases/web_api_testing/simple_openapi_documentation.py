import json
import os
from dataclasses import field
from typing import Dict

import yaml
from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.web_api_testing.documentation.openapi_specification_handler import OpenAPISpecificationHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptContext
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Context, Prompt
from hackingBuddyGPT.usecases.web_api_testing.utils.evaluator import Evaluator
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


class SimpleWebAPIDocumentation(Agent):
    """
    Agent to document REST APIs of a website by interacting with them and generating an OpenAPI specification.
    """
    llm: OpenAILib
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False
    config_path: str = parameter(
        desc="Configuration file path",
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
    def categorize_endpoints(self, endpoints, query:dict):
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
    def init(self):
        """Initialize the agent with configurations, capabilities, and handlers."""
        super().init()
        self.found_all_http_methods: bool = False
        if self.config_path != "":
            self.config_path = os.path.join("src/hackingBuddyGPT/usecases/web_api_testing/configs/", self.config_path)
        config = self._load_config(self.config_path)
        self.token, self.host, self.description, self.correct_endpoints, self.query_params = (
            config.get("token"), config.get("host"), config.get("description"), config.get("correct_endpoints"), config.get("query_params")
        )
        self.all_steps_done = False

        self.categorized_endpoints = self.categorize_endpoints( self.correct_endpoints, self.query_params)

        if "spotify" in self.config_path:

            os.environ['SPOTIPY_CLIENT_ID'] = config['client_id']
            os.environ['SPOTIPY_CLIENT_SECRET'] = config['client_secret']
            os.environ['SPOTIPY_REDIRECT_URI'] = config['redirect_uri']
        print(f'Host:{self.host}')
        self._setup_capabilities()
        self.strategy = PromptStrategy.CHAIN_OF_THOUGHT
        self.prompt_context = PromptContext.DOCUMENTATION
        self.llm_handler = LLMHandler(self.llm, self._capabilities)
        self.response_handler = ResponseHandler(self.llm_handler, self.prompt_context)
        self.documentation_handler = OpenAPISpecificationHandler(
            self.llm_handler, self.response_handler, self.strategy
        )

        self.evaluator = Evaluator(config=config)
        self._setup_initial_prompt()

    def _load_config(self, path):
        """Loads JSON configuration from the specified path."""
        with open(path, 'r') as file:
            return json.load(file)

    def _setup_capabilities(self):
        """Initializes agent's capabilities for API documentation."""
        self._capabilities = {
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(self._context["notes"])
        }

    def _setup_initial_prompt(self):
        """Configures the initial prompt for the documentation process."""
        initial_prompt = {
            "role": "system",
            "content": (
                f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                f"The website is {self.description}. Start with an empty OpenAPI specification and be meticulous in "
                f"documenting your observations as you traverse the APIs."
            ),
        }
        self._prompt_history.append(initial_prompt)
        self.prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            history=self._prompt_history,
            handlers=(self.llm_handler, self.response_handler),
            context=self.prompt_context,
            open_api_spec=self.documentation_handler.openapi_spec,
            rest_api_info=(self.token, self.host, self.correct_endpoints, self.categorized_endpoints)
        )

    def all_http_methods_found(self, turn: int) -> bool:
        """Checks if all expected HTTP methods have been found."""
        found_count = sum(len(endpoints) for endpoints in self.documentation_handler.endpoint_methods.values())
        expected_count = len(self.documentation_handler.endpoint_methods.keys()) * 4
        if found_count >= len(self.correct_endpoints) and self.all_steps_done:
            self.found_all_http_methods = True
        return self.found_all_http_methods

    def perform_round(self, turn: int) -> bool:
        """Executes a round of API documentation based on the turn number."""
        if turn == 1:
            self._explore_mode(turn)
        elif turn < 20:
            self._single_exploit_run(turn)
        else:
            self._exploit_until_no_help_needed(turn)
        return self.all_http_methods_found(turn)

    def _explore_mode(self, turn: int) -> None:
        """Initiates explore mode on the first turn."""
        last_endpoint_found_x_steps_ago, new_endpoint_count = 0, len(self.documentation_handler.endpoint_methods)
        last_found_endpoints = len(self.prompt_engineer.prompt_helper.found_endpoints)

        while (
            last_endpoint_found_x_steps_ago <= new_endpoint_count + 5
            and last_endpoint_found_x_steps_ago <= 10
            and not self.found_all_http_methods
        ):
            self.run_documentation(turn, "explore")
            current_count = len(self.prompt_engineer.prompt_helper.found_endpoints)
            last_endpoint_found_x_steps_ago = last_endpoint_found_x_steps_ago + 1 if current_count == last_found_endpoints else 0
            last_found_endpoints = current_count
            if (updated_count := len(self.documentation_handler.endpoint_methods)) > new_endpoint_count:
                new_endpoint_count = updated_count
                self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec

    def _exploit_until_no_help_needed(self, turn: int) -> None:
        """Runs exploit mode continuously until no endpoints need help."""
        while self.prompt_engineer.prompt_helper.get_endpoints_needing_help():
            self.run_documentation(turn, "exploit")
            self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec

    def _single_exploit_run(self, turn: int) -> None:
        """Executes a single exploit run."""
        self.run_documentation(turn, "exploit")
        self.prompt_engineer.open_api_spec = self.documentation_handler.openapi_spec

    def has_no_numbers(self, path: str) -> bool:
        """Returns True if the given path contains no numbers."""
        return not any(char.isdigit() for char in path)

    def run_documentation(self, turn: int, move_type: str) -> None:
        """Runs the documentation process for the given turn and move type."""
        is_good = False
        while not is_good:
            prompt = self.prompt_engineer.generate_prompt(turn=turn, move_type=move_type,log=self._log , prompt_history=self._prompt_history, llm_handler =self.llm_handler)
            response, completion = self.llm_handler.execute_prompt(prompt=prompt)
            is_good, self._prompt_history, result, result_str = self.prompt_engineer.evaluate_response(response, completion, self._prompt_history, self._log)
            if result == None:
                continue
            self._prompt_history, self.prompt_engineer = self.documentation_handler.document_response(
                 result, response, result_str, self._prompt_history, self.prompt_engineer
            )

            if self.prompt_engineer.prompt_helper.current_step == 6:
                self.all_steps_done = True

            # Use evaluator to record routes and parameters found
            #routes_found = self.all_http_methods_found(turn)
            #query_params_found = self.evaluator.all_query_params_found(turn)  # This function should return the number found
            #false_positives = self.evaluator.check_false_positives(response)  # Define this function to determine FP count

            # Record these results in the evaluator
            #self.evaluator.results["routes_found"].append(routes_found)
            #self.evaluator.results["query_params_found"].append(query_params_found)
            #self.evaluator.results["false_positives"].append(false_positives)
       # self.finalize_documentation_metrics()

        self.all_http_methods_found(turn)

    def finalize_documentation_metrics(self):
        """Calculate and log the final effectiveness metrics after documentation process is complete."""
        metrics = self.evaluator.calculate_metrics()
        print("Documentation Effectiveness Metrics:")
        print(f"Percent Routes Found: {metrics['Percent Routes Found']:.2f}%")
        print(f"Percent Parameters Found: {metrics['Percent Parameters Found']:.2f}%")
        print(f"Average False Positives: {metrics['Average False Positives']}")
        print(f"Routes Found - Best: {metrics['Routes Best/Worst'][0]}, Worst: {metrics['Routes Best/Worst'][1]}")
        print(
            f"Query Parameters Found - Best: {metrics['Params Best/Worst'][0]}, Worst: {metrics['Params Best/Worst'][1]}")


@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPIDocumentationUseCase(AutonomousAgentUseCase[SimpleWebAPIDocumentation]):
    """Use case for the SimpleWebAPIDocumentation agent."""
    pass
