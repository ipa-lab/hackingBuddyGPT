import copy
import json
import os.path
import re
from dataclasses import field
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
from hackingBuddyGPT.usecases.web_api_testing.utils.configuration_handler import ConfigurationHandler
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
        _all_test_cases_run (bool): Flag indicating if all HTTP methods have been found.
    """

    llm: OpenAILib
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
    _context: Context = field(default_factory=lambda: {"notes": list(), "test_cases": list(), "parsed":list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_test_cases_run: bool = False

    def init(self):
        super().init()
        configuration_handler = ConfigurationHandler(self.config_path, self.strategy_string)
        self.config, self.strategy = configuration_handler.load()
        self.token, self.host, self.description, self.correct_endpoints, self.query_params= configuration_handler._extract_config_values(self.config)
        self._load_openapi_specification()
        self._setup_environment()
        self._setup_handlers()
        self._setup_initial_prompt()
        self.last_prompt = ""


    def _load_openapi_specification(self):
        if os.path.exists(self.config_path):
            self._openapi_specification_parser = OpenAPISpecificationParser(self.config_path)
            self._openapi_specification = self._openapi_specification_parser.api_data

    def _setup_environment(self):
        self._context["host"] = self.host
        self._setup_capabilities()
        self.categorized_endpoints = self._openapi_specification_parser.categorize_endpoints(self.correct_endpoints, self.query_params)
        self.prompt_context = PromptContext.PENTESTING

    def _setup_handlers(self):
        self._llm_handler = LLMHandler(self.llm, self._capabilities, all_possible_capabilities=self.all_capabilities)
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)
        if "username" in self.config.keys() and "password" in self.config.keys():
            username = self.config.get("username")
            password = self.config.get("password")
        else:
            username = "test"
            password = "<PASSWORD>"
        self.pentesting_information = PenTestingInformation(self._openapi_specification_parser, self.config)
        self._response_handler = ResponseHandler(
            llm_handler=self._llm_handler, prompt_context=self.prompt_context, prompt_helper=self.prompt_helper,
            config=self.config, pentesting_information = self.pentesting_information )
        self.response_analyzer = ResponseAnalyzerWithLLM(llm_handler=self._llm_handler,
                                                         pentesting_info=self.pentesting_information,
                                                         capacity=self.parse_capacity,
                                                         prompt_helper = self.prompt_helper)
        self._response_handler.set_response_analyzer(self.response_analyzer)
        self._report_handler = ReportHandler(self.config)
        self._test_handler = TestHandler(self._llm_handler)


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
        self.python_test_case_capability = {"python_test_case": PythonTestCase(test_cases)}
        self.parse_capacity = {"parse": ParsedInformation(test_cases)}
        self._capabilities = {
            "http_request": HTTPRequest(self.host)        }
        self.all_capabilities = {"python_test_case": PythonTestCase(test_cases), "parse": ParsedInformation(test_cases),"http_request": HTTPRequest(self.host),
            "record_note": RecordNote(notes)}
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
        while self.purpose == self.prompt_engineer._purpose:
            prompt = self.prompt_engineer.generate_prompt(turn=turn, move_type="explore",
                                                          prompt_history=self._prompt_history)

            response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt,"http_request" )
            self._handle_response(completion, response)

        self.purpose = self.prompt_engineer._purpose
        if self.purpose == PromptPurpose.LOGGING_MONITORING:
            self.pentesting_information.next_testing_endpoint()

    def _handle_response(self, completion: Any, response: Any) -> None:
        """
        Handles the response from the LLM. Parses the response, executes the necessary actions,
        and updates the prompt history.

        Args:
            completion (Any): The completion object from the LLM.
            response (Any): The response object from the LLM.
            purpose (str): The purpose or intent behind the response handling.
        """



        with self.log.console.status("[bold green]Executing that command..."):
            if response is None:
                return

            print(f'type:{type(response)}')


            response = self.adjust_action(response)

            result = self.execute_response(response, completion)

            #self._report_handler.write_vulnerability_to_report(self.prompt_helper.current_sub_step, self.prompt_helper.current_test_step, result, self.prompt_helper.counter)
            #
            #analysis, status_code = self._response_handler.evaluate_result(
            #    result=result,
            #    prompt_history=self._prompt_history,
            #    analysis_context= self.prompt_engineer.prompt_helper.current_test_step)
            #
            #if self.purpose != PromptPurpose.SETUP:
            #    self._prompt_history = self._test_handler.generate_test_cases(
            #    analysis=analysis,
            #    endpoint=response.action.path,
            #    method=response.action.method,
            #    prompt_history=self._prompt_history, status_code=status_code)
            #
            #    self._report_handler.write_analysis_to_report(analysis=analysis, purpose=self.prompt_engineer._purpose)
        if self.prompt_engineer._purpose == PromptPurpose.LOGGING_MONITORING:
            self.all_test_cases_run()

    def extract_ids(self, data, id_resources=None, parent_key=''):
        if id_resources is None:
            id_resources = {}

        # If the data is a dictionary, iterate over each key-value pair
        if isinstance(data, dict):
            for key, value in data.items():
                # Update the key to reflect nested structures
                new_key = f"{parent_key}.{key}" if parent_key else key

                # Check for 'id' in the key to classify it appropriately
                if 'id' in key and isinstance(value, str):
                    # Determine the category based on the key name before 'id'
                    category = key.replace('id', '').rstrip('_').lower()  # Normalize the key
                    if category == '':  # If no specific category, it could just be 'id'
                        category = parent_key.split('.')[-1]  # Use parent key as category
                    category = category.rstrip('s')  # Singular form for consistency
                    if category != "id":
                        category = category + "_id"

                    # Append the ID to the appropriate category list
                    if category in id_resources:
                        id_resources[category].append(value)
                    else:
                        id_resources[category] = [value]
                else:
                    # Recursively search for ids within nested dictionaries or lists
                    self.extract_ids(value, id_resources, new_key)

        # If the data is a list, apply the function recursively to each item
        elif isinstance(data, list):
            for index, item in enumerate(data):
                self.extract_ids(item, id_resources, f"{parent_key}[{index}]")

        return id_resources
    def extract_resource_name(self, path: str) -> str:
        """
        Extracts the key resource word from a path.

        Examples:
          - '/identity/api/v2/user/videos/{video_id}' -> 'video'
          - '/workshop/api/shop/orders/{order_id}'    -> 'order'
          - '/community/api/v2/community/posts/{post_id}/comment' -> 'comment'
        """
        # Split into non-empty segments
        parts = [p for p in path.split('/') if p]
        if not parts:
            return ""

        last_segment = parts[-1]

        # 1) If last segment is a placeholder like "{video_id}", return 'video'
        #    i.e., capture the substring before "_id".
        match = re.match(r'^\{(\w+)_id\}$', last_segment)
        if match:
            return match.group(1)  # e.g. 'video', 'order'

        # 2) Otherwise, if the last segment is a word like "videos" or "orders",
        #    strip a trailing 's' (e.g., "videos" -> "video").
        if last_segment.endswith('s'):
            return last_segment[:-1]

        # 3) If it's just "comment" or a similar singular word, return as-is
        return last_segment


    def extract_token_from_http_response(self, http_response):
            """
            Extracts the token from an HTTP response body.

            Args:
                http_response (str): The raw HTTP response as a string.

            Returns:
                str: The extracted token if found, otherwise None.
            """
            # Split the HTTP headers from the body
            try:
                headers, body = http_response.split("\r\n\r\n", 1)
            except ValueError:
                # If no double CRLF is found, return None
                return None

            try:
                # Parse the body as JSON
                body_json = json.loads(body)
                # Extract the token
                if "token" in body_json.keys():
                    return body_json["token"]
                elif "authentication" in body_json.keys():
                    return body_json.get("authentication", {}).get("token", None)
            except json.JSONDecodeError:
                # If the body is not valid JSON, return None
                return None

    def save_resource(self, path, data):
        resource = self.extract_resource_name(path)
        if resource != "" and resource not in self.prompt_helper.current_user.keys():
            self.prompt_helper.current_user[resource] = []
        if data not in self.prompt_helper.current_user[resource]:
            self.prompt_helper.current_user[resource].append(data)
            for i, account in enumerate(self.prompt_helper.accounts):
                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    self.pentesting_information.accounts[i][resource] = self.prompt_helper.current_user[resource]

    def set_and_get_token(self, result):

        if "token" in result and (not self.token or self.token == "your_api_token_here" or self.token == ""):
            self.token = self.extract_token_from_http_response(result)
            for account in self.prompt_helper.accounts:
                if account.get("x") == self.prompt_helper.current_user.get("x") and "token" not in account.keys():
                    account["token"] = self.token
            self.prompt_helper.accounts = self.pentesting_information.accounts
            # self.pentesting_information.set_valid_token(self.token)
        if self.token and "token" not in self.prompt_helper.current_user:
            self.prompt_helper.current_user["token"] = self.token

        print(f'self.token:{self.token}')


    def adjust_user(self, result):
        headers, body = result.split("\r\n\r\n", 1)
        print(f'body:{body}')
        if "html" in body:
            return

        if "key" in body:
            data = json.loads(body)
            for account in self.prompt_helper.accounts:
                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    account["key"] = data.get("key")
        if "posts" in body:
            data = json.loads(body)
            # Extract ids
            id_resources = self.extract_ids(data)
            if len(self.pentesting_information.resources) == 0:
                self.pentesting_information.resources = id_resources
            else:
                self.pentesting_information.resources.update(id_resources)

        if "id" in body and self.prompt_helper.current_sub_step.get("purpose") == PromptPurpose.SETUP:
            data = json.loads(body)
            user_id = data.get('id')
            for account in self.prompt_helper.accounts:

                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    account["id"] = user_id
                    break

    def adjust_action(self, response:Any):
        old_response = copy.deepcopy(response)

        print(f'response:{response}')
        print(f'response.action:{response.action}')
        print(f'response.action.path:{response.action.path}')
        if self.prompt_engineer._purpose == PromptPurpose.SETUP:
            response.action.method = "POST"

        token = self.prompt_helper.current_sub_step.get("token")
        print(f'token:{token}')
        if token and (token != "" or token is not None):
            if self.config.get("name") == "vAPI":
                response.action.headers = {"Authorization-Token": f"{token}"}
            elif self.config.get("name") == "crapi":
                response.action.headers = {"Authorization": f"Bearer {token}"}

            else:

                response.action.headers = {"Authorization-Token": f"Bearer {token}"}

        if response.action.path != self.prompt_helper.current_sub_step.get("path"):
            response.action.path = self.prompt_helper.current_sub_step.get("path")

        if response.action.path and "_id}" in response.action.path:
            if response.action.__class__.__name__ != "HTTPRequest":
                self.save_resource(response.action.path, response.action.data)

        if isinstance(response.action.path, dict):
            response.action.path = response.action.path.get("path")

        if response.action.body is None:
            response.action.body = self.prompt_helper.current_user
        print(f'response:{response}')

        if response.action.path is None:
            response.action.path = old_response.action.path
        print(f' adjusted response:{response}')

        return response

    def execute_response(self, response, completion):
        message = completion.choices[0].message
        tool_call_id: str = message.tool_calls[0].id
        command: str = pydantic_core.to_json(response).decode()
        self.log.console.print(Panel(command, title="assistant"))
        self._prompt_history.append(message)

        result: Any = response.execute()
        self.log.console.print(Panel(result, title="tool"))
        if not isinstance(result, str):
            endpoint: str = str(response.action.path).split("/")[1]
            self._report_handler.write_endpoint_to_report(endpoint)

        self._prompt_history.append(
            tool_message(self._response_handler.extract_key_elements_of_response(result), tool_call_id))

        self.set_and_get_token(result)

        self.adjust_user(result)
        print(f' accounts after request:{self.pentesting_information.accounts}')
        return result



@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPITestingUseCase(AutonomousAgentUseCase[SimpleWebAPITesting]):
    """
    A use case for the SimpleWebAPITesting agent, encapsulating the setup and execution
    of the web API testing scenario.
    """

    pass
