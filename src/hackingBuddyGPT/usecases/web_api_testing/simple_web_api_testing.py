import copy
import json
import os.path
import re
from dataclasses import field
from typing import Any, Dict, List

import pydantic_core
from rich.panel import Panel

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.parsed_information import ParsedInformation
from hackingBuddyGPT.capabilities.python_test_case import PythonTestCase
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.base import AutonomousUseCase, use_case
from hackingBuddyGPT.utils.capability_manager import CapabilityManager
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose
from hackingBuddyGPT.utils.openapi.openapi_parser import OpenAPISpecificationParser
from hackingBuddyGPT.usecases.web_api_testing.report_handler import ReportHandler
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.prompt_engineer import PromptEngineer
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer_with_llm import \
    ResponseAnalyzerWithLLM
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.test_handler import GenerationTestHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.configuration_handler import ConfigurationHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Context, Prompt
from hackingBuddyGPT.usecases.web_api_testing.utils.llm_handler import LLMHandler
from hackingBuddyGPT.utils import tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


# OpenAPI specification file path

@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPITesting(AutonomousUseCase):
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

    llm: OpenAILib = None
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
    _capabilities: CapabilityManager = None
    _all_test_cases_run: bool = False

    def init(self):
        super().init()
        configuration_handler = ConfigurationHandler(self.config_path, self.strategy_string)
        self.config, self.strategy = configuration_handler.load()
        self.token, self.host, self.description, self.correct_endpoints, self.query_params = configuration_handler._extract_config_values(
            self.config)
        self._load_openapi_specification()
        self._setup_environment()
        self._setup_handlers()
        self._setup_initial_prompt()
        self.last_prompt = ""

    def get_name(self) -> str:
        return self.__class__.__name__

    def _load_openapi_specification(self):
        """
           Loads the OpenAPI specification from the configured file path.

           If the config path exists, it initializes the `OpenAPISpecificationParser` and stores both
           the parser instance and the parsed OpenAPI spec data.
           """
        if os.path.exists(self.config_path):
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
        self._capabilities = CapabilityManager(self.log)
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
            - Test case handler for saving and generating test cases.

            If username and password are not found in the config, defaults are used.
            """
        self._llm_handler = LLMHandler(self.llm, self._capabilities._capabilities, all_possible_capabilities=self.all_capabilities)
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
            config=self.config, pentesting_information=self.pentesting_information)
        self.response_analyzer = ResponseAnalyzerWithLLM(llm_handler=self._llm_handler,
                                                         pentesting_info=self.pentesting_information,
                                                         capacity=self.parse_capacity,
                                                         prompt_helper=self.prompt_helper)
        self._response_handler.set_response_analyzer(self.response_analyzer)
        self._report_handler = ReportHandler(self.config)
        self._test_handler = GenerationTestHandler(self._llm_handler)

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
        self.all_capabilities = {"python_test_case": PythonTestCase(test_cases), "parse": ParsedInformation(test_cases),
                                 "http_request": HTTPRequest(self.host),
                                 "record_note": RecordNote(notes)}
        self.http_capability = {"http_request": HTTPRequest(self.host),
                                }

    def perform_round(self, turn: int) -> None:
        """
        Performs a single round of interaction with the LLM. Generates a prompt, sends it to the LLM,
        and handles the response.

        Args:
            turn (int): The current round number.
        """
        self._perform_prompt_generation(turn)
        if len(self.prompt_engineer.pentesting_information.pentesting_step_list) == 0:
            self.all_test_cases_run()
            return
        if turn == 20:
            self._report_handler.save_report()

    def _perform_prompt_generation(self, turn: int) -> None:
        response: Any
        completion: Any
        while self.purpose == self.prompt_engineer._purpose and not self._all_test_cases_run:
            prompt = self.prompt_engineer.generate_prompt(turn=turn, move_type="explore",
                                                          prompt_history=self._prompt_history)

            response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt, "http_request")
            self._handle_response(completion, response)
            if len(self.prompt_engineer.pentesting_information.pentesting_step_list) == 0:
                self.all_test_cases_run()
                return

        self.purpose = self.prompt_engineer._purpose


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


            response = self.adjust_action(response)

            result = self.execute_response(response, completion)

            self._report_handler.write_vulnerability_to_report(self.prompt_helper.current_sub_step,
                                                               self.prompt_helper.current_test_step, result,
                                                               self.prompt_helper.counter)

            analysis, status_code = self._response_handler.evaluate_result(
                result=result,
                prompt_history=self._prompt_history,
                analysis_context=self.prompt_engineer.prompt_helper.current_test_step)

            if self.purpose != PromptPurpose.SETUP:
                self._prompt_history = self._test_handler.generate_test_cases(
                    analysis=analysis,
                    endpoint=response.action.path,
                    method=response.action.method,
                    body=response.action.body,
                    prompt_history=self._prompt_history, status_code=status_code)

                self._report_handler.write_analysis_to_report(analysis=analysis, purpose=self.prompt_engineer._purpose)

    def extract_ids(self, data, id_resources=None, parent_key=''):
        """
           Recursively extracts all string-based identifiers (IDs) from a nested data structure.

           This method traverses a deeply nested dictionary or list (e.g., a parsed JSON response)
           and collects all keys that contain `"id"` and have string values. It organizes these IDs
           into a dictionary grouped by normalized resource categories based on the key names.

           Args:
               data (Union[dict, list]): The input data structure (e.g., API response) to search for IDs.
               id_resources (dict, optional): A dictionary used to accumulate found IDs, grouped by category.
                                              If None, a new dictionary is initialized.
               parent_key (str, optional): The key path used for context when processing nested fields.

           Returns:
               dict: A dictionary where keys are derived categories (e.g., `"user_id"`, `"post_id"`) and
                     values are lists of extracted ID strings.

           """
        if id_resources is None:
            id_resources = {}
        if isinstance(data, dict):
            for key, value in data.items():
                # Update the key to reflect nested structures
                new_key = f"{parent_key}.{key}" if parent_key else key
                if 'id' in key and isinstance(value, str):
                    # Determine the category based on the key name before 'id'
                    category = key.replace('id', '').rstrip('_').lower()  # Normalize the key
                    if category == '':  # If no specific category, it could just be 'id'
                        category = parent_key.split('.')[-1]  # Use parent key as category
                    category = category.rstrip('s')  # Singular form for consistency
                    if category != "id":
                        category = category + "_id"

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
        """
          Saves a discovered API resource and its associated data to the current user context.

          This method extracts the resource name from the given API path (e.g., from `/users/1/posts` → `posts`),
          then stores the provided `data` under that resource for the current user in `prompt_helper.current_user`.

          If the resource does not already exist in the user's data, it initializes it as an empty list.
          It also updates the corresponding account entry in `pentesting_information.accounts` to ensure
          consistency across known user accounts.

          Args:
              path (str): The API endpoint path from which to extract the resource name.
              data (Any): The resource data to be saved under the extracted resource name.
          """
        resource = self.extract_resource_name(path)
        if resource != "" and resource not in self.prompt_helper.current_user.keys():
            self.prompt_helper.current_user[resource] = []
        if data not in self.prompt_helper.current_user[resource]:
            self.prompt_helper.current_user[resource].append(data)
            for i, account in enumerate(self.prompt_helper.accounts):
                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    self.pentesting_information.accounts[i][resource] = self.prompt_helper.current_user[resource]

    def adjust_user(self, result):
        """
            Adjusts the current user and pentesting state based on the contents of an HTTP response.

            This method parses the HTTP response into headers and body, and inspects the body for specific
            keys such as `"key"`, `"posts"`, and `"id"` to update user-related data structures accordingly.

            Behavior:
            - If the body contains `"html"`, the method returns early (assumed to be an invalid or non-JSON response).
            - If `"key"` is found:
                - Parses the body and updates the `"key"` field of the matching user in `prompt_helper.accounts`.
            - If `"posts"` is found:
                - Parses the body, extracts resource IDs, and updates `pentesting_information.resources`.
            - If `"id"` is found and the current sub-step purpose is `PromptPurpose.SETUP`:
                - Extracts the user ID from the body and stores it in the matching user account.

            Args:
                result (str): The full HTTP response string including headers and body (separated by `\r\n\r\n`).
            """
        if "Could not" in result:
            return
        headers, body = result.split("\r\n\r\n", 1)
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

    def adjust_action(self, response: Any):
        """
        Modifies the action of an API response object based on the current prompt context and configuration.

        This method is typically used during API test setup or fuzzing to:
        - Modify the HTTP method (e.g., set to POST during setup).
        - Inject authorization tokens into the request headers based on the API type (`vAPI`, `crapi`, etc.).
        - Correct or override request paths and bodies with current user context.
        - Optionally save resource data if the path contains identifiable parameters (e.g., `_id`).

        Args:
            response (Any): The response object containing an `action` field (with `method`, `headers`, `path`, `body`, etc.).

        Returns:
            Any: The updated response object with modified action values based on prompt context and configuration.
        """
        old_response = copy.deepcopy(response)
        if self.prompt_engineer._purpose == PromptPurpose.SETUP:
            response.action.method = "POST"

        token = self.prompt_helper.current_sub_step.get("token")
        if token is not None and "{{" in token:
            for account in self.prompt_helper.accounts:
                if account["x"] == self.prompt_helper.current_user["x"]:
                    token = account["token"]
                    break
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

        if response.action.path is None:
            response.action.path = old_response.action.path

        return response

    def execute_response(self, response, completion):
        """
            Executes the API response, logs it, and updates internal state for documentation and testing.

            This method performs the following actions:
            - Converts the `response` object to JSON and prints it as an assistant message.
            - Executes the response as a tool call (i.e., performs the API request).
            - Logs and prints the tool response.
            - If the result is not a string, it attempts to extract the endpoint name and write it to a report.
            - Appends a tool message with key elements extracted from the result to the prompt history.
            - Adjusts user-related state based on the result (e.g., tokens, user IDs).
            - Prints the state of user accounts after the request for debugging.

            Args:
                response (Any): The response object that encapsulates the tool call to be executed.
                completion (Any): The LLM completion object, including metadata like the tool call ID.

            Returns:
                Any: The result of executing the tool call (typically a string or structured object).
            """
        message = completion.choices[0].message
        tool_call_id: str = message.tool_calls[0].id
        command: str = pydantic_core.to_json(response).decode()
        self.log.console.print(Panel(command, title="assistant"))
        msg = {"role": message.role, "content": message.content, "tool_calls": message.tool_calls}
        self._prompt_history.append(msg)
        result: Any = response.execute()
        self.log.console.print(Panel(result, title="tool"))
        if not isinstance(result, str):
            endpoint: str = str(response.action.path).split("/")[1]
            self._report_handler.write_endpoint_to_report(endpoint)

        self._prompt_history.append(tool_message(self._response_handler.extract_key_elements_of_response(result), tool_call_id))

        self.adjust_user(result)
        return result