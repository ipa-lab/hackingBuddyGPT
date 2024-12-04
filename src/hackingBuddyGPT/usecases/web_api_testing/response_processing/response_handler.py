import json
import re
from collections import Counter
from itertools import cycle
from typing import Any, Dict, Optional, Tuple
import random
from urllib.parse import urlencode
import pydantic_core
from bs4 import BeautifulSoup
from rich.panel import Panel

from hackingBuddyGPT.usecases.web_api_testing.documentation.pattern_matcher import PatternMatcher
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptContext
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.pentesting_information import (
    PenTestingInformation,
)
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer_with_llm import (
    ResponseAnalyzerWithLLM,
)
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Prompt
from hackingBuddyGPT.utils import tool_message


class ResponseHandler:
    """
    ResponseHandler is a class responsible for handling various types of responses from an LLM (Large Language Model).
    It processes prompts, parses HTTP responses, extracts examples, and handles OpenAPI specifications.

    Attributes:
        llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        pentesting_information (PenTestingInformation): An instance containing pentesting information.
        response_analyzer (ResponseAnalyzerWithLLM): An instance for analyzing responses with the LLM.
    """

    def __init__(self, llm_handler: LLMHandler, prompt_context: PromptContext, config: Any,
                 prompt_helper: PromptGenerationHelper, pentesting_information: PenTestingInformation = None) -> None:
        """
        Initializes the ResponseHandler with the specified LLM handler.

        Args:
            llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        """
        self.llm_handler = llm_handler
        self.no_action_counter = 0
        if prompt_context == PromptContext.PENTESTING:
            self.pentesting_information = pentesting_information


        self.common_endpoints = ['/api', '/auth', '/login', '/admin', '/register', '/users', '/photos', '/images',
                                 '/products', '/orders',
                                 '/search', '/posts', '/todos', '/1', '/resources', '/categories',
                                 '/cart', '/checkout', '/payments', '/transactions', '/invoices', '/teams', '/comments',
                                 '/jobs',
                                 '/notifications', '/messages', '/files', '/settings', '/status', '/health',
                                 '/healthcheck',
                                 '/info', '/docs', '/swagger', '/openapi', '/metrics', '/logs', '/analytics',
                                 '/feedback',
                                 '/support', '/profile', '/account', '/reports', '/dashboard', '/activity',
                                 '/subscriptions', '/webhooks',
                                 '/events', '/upload', '/download', '/images', '/videos', '/user/login', '/api/v1',
                                 '/api/v2',
                                 '/auth/login', '/auth/logout', '/auth/register', '/auth/refresh', '/users/{id}',
                                 '/users/me', '/products/{id}'
                                              '/users/profile', '/users/settings', '/products/{id}', '/products/search',
                                 '/orders/{id}',
                                 '/orders/history', '/cart/items', '/cart/checkout', '/checkout/confirm',
                                 '/payments/{id}',
                                 '/payments/methods', '/transactions/{id}', '/transactions/history',
                                 '/notifications/{id}',
                                 '/messages/{id}', '/messages/send', '/files/upload', '/files/{id}', '/admin/users',
                                 '/admin/settings',
                                 '/settings/preferences', '/search/results', '/feedback/{id}', '/support/tickets',
                                 '/profile/update',
                                 '/password/reset', '/password/change', '/account/delete', '/account/activate',
                                 '/account/deactivate',
                                 '/account/settings', '/account/preferences', '/reports/{id}', '/reports/download',
                                 '/dashboard/stats',
                                 '/activity/log', '/subscriptions/{id}', '/subscriptions/cancel', '/webhooks/{id}',
                                 '/events/{id}',
                                 '/images/{id}', '/videos/{id}', '/files/download/{id}', '/support/tickets/{id}']
        self.common_endpoints_categorized = self.categorize_endpoints()
        self.query_counter = 0
        self.repeat_counter = 0
        self.variants_of_found_endpoints = []
        self.name= config.get("name")
        self.token = config.get("token")
        self.last_path = ""
        self.prompt_helper = prompt_helper
        self.pattern_matcher = PatternMatcher()
        self.saved_endpoints = {}

    def categorize_endpoints(self):
        root_level = []
        single_parameter = []
        subresource = []
        related_resource = []
        multi_level_resource = []

        # Iterate through the cycle of endpoints
        for endpoint in self.common_endpoints:
            parts = [part for part in endpoint.split('/') if part]

            if len(parts) == 1:
                root_level.append(endpoint)
            elif len(parts) == 2:
                if "{id}" in parts[1]:
                    single_parameter.append(endpoint)
                else:
                    subresource.append(endpoint)
            elif len(parts) == 3:
                if any("{id}" in part for part in parts):
                    related_resource.append(endpoint)
                else:
                    multi_level_resource.append(endpoint)
            else:
                multi_level_resource.append(endpoint)

        return {
            1: cycle(root_level),
            2: cycle(single_parameter),
            3: cycle(subresource),
            4: cycle(related_resource),
            5: cycle(multi_level_resource),
        }

    def get_response_for_prompt(self, prompt: str) -> object:
        """
        Sends a prompt to the LLM's API and retrieves the response.

        Args:
            prompt (str): The prompt to be sent to the API.

        Returns:
            str: The response from the API.
        """
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        response, completion = self.llm_handler.execute_prompt(messages)
        return response, completion

    def parse_http_status_line(self, status_line: str) -> str:
        """
        Parses an HTTP status line and returns the status code and message.

        Args:
            status_line (str): The HTTP status line to be parsed.

        Returns:
            str: The parsed status code and message.

        Raises:
            ValueError: If the status line is invalid.
        """
        if status_line == "Not a valid HTTP method" or "note recorded" in status_line:
            return status_line
        status_line = status_line.split("\r\n")[0]
        # Regular expression to match valid HTTP status lines
        match = re.match(r"^(HTTP/\d\.\d) (\d{3}) (.*)$", status_line)
        if match:
            protocol, status_code, status_message = match.groups()
            return f"{status_code} {status_message}"
        else:
            raise ValueError(f"{status_line} is an invalid HTTP status line")

    def extract_response_example(self, html_content: str) -> Optional[Dict[str, Any]]:
        """
        Extracts the JavaScript example code and result placeholder from HTML content.

        Args:
            html_content (str): The HTML content containing the example code.

        Returns:
            Optional[Dict[str, Any]]: The extracted response example as a dictionary, or None if extraction fails.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        example_code = soup.find("code", {"id": "example"})
        result_code = soup.find("code", {"id": "result"})
        if example_code and result_code:
            example_text = example_code.get_text()
            result_text = result_code.get_text()
            return json.loads(result_text)
        return None

    def parse_http_response_to_openapi_example(
            self, openapi_spec: Dict[str, Any], http_response: str, path: str, method: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]:
        """
        Parses an HTTP response to generate an OpenAPI example.

        Args:
            openapi_spec (Dict[str, Any]): The OpenAPI specification to update.
            http_response (str): The HTTP response to parse.
            path (str): The API path.
            method (str): The HTTP method.

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]: A tuple containing the entry dictionary, reference, and updated OpenAPI specification.
        """

        headers, body = http_response.split("\r\n\r\n", 1)
        try:
            body_dict = json.loads(body)
        except json.decoder.JSONDecodeError:
            return None, None, openapi_spec

        reference, object_name, openapi_spec = self.parse_http_response_to_schema(openapi_spec, body_dict, path)
        entry_dict = {}

        if len(body_dict) == 1:
            entry_dict["id"] = {"value": body_dict}
            self.llm_handler.add_created_object(entry_dict, object_name)
        else:
            if isinstance(body_dict, list):
                for entry in body_dict:
                    key = entry.get("title") or entry.get("name") or entry.get("id")
                    entry_dict[key] = {"value": entry}
                    self.llm_handler.add_created_object(entry_dict[key], object_name)
                    if len(entry_dict) > 3:
                        break
            else:
                key = body_dict.get("title") or body_dict.get("name") or body_dict.get("id")
                entry_dict[key] = {"value": body_dict}
                self.llm_handler.add_created_object(entry_dict[key], object_name)

        return entry_dict, reference, openapi_spec

    def extract_description(self, note: Any) -> str:
        """
        Extracts the description from a note.

        Args:
            note (Any): The note containing the description.

        Returns:
            str: The extracted description.
        """
        return note.action.content

    def parse_http_response_to_schema(
            self, openapi_spec: Dict[str, Any], body_dict: Dict[str, Any], path: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Parses an HTTP response body to generate an OpenAPI schema.

        Args:
            openapi_spec (Dict[str, Any]): The OpenAPI specification to update.
            body_dict (Dict[str, Any]): The HTTP response body as a dictionary or list.
            path (str): The API path.

        Returns:
            Tuple[str, str, Dict[str, Any]]: A tuple containing the reference, object name, and updated OpenAPI specification.
        """
        if "/" not in path:
            return None, None, openapi_spec

        object_name = path.split("/")[1].capitalize().rstrip("s")
        properties_dict = {}

        # Handle different structures of `body_dict`
        if isinstance(body_dict, dict):
            for key, value in body_dict.items():
                # If it's a nested dictionary, extract keys recursively
                properties_dict = self.extract_keys(key, value, properties_dict)

        elif isinstance(body_dict, list) and len(body_dict) > 0:
            first_item = body_dict[0]
            if isinstance(first_item, dict):
                for key, value in first_item.items():
                    properties_dict = self.extract_keys(key, value, properties_dict)

        # Create the schema object for this response
        object_dict = {"type": "object", "properties": properties_dict}

        # Add the schema to OpenAPI spec if not already present
        if object_name not in openapi_spec["components"]["schemas"]:
            openapi_spec["components"]["schemas"][object_name] = object_dict

        reference = f"#/components/schemas/{object_name}"
        return reference, object_name, openapi_spec

    def read_yaml_to_string(self, filepath: str) -> Optional[str]:
        """
        Reads a YAML file and returns its contents as a string.

        Args:
            filepath (str): The path to the YAML file.

        Returns:
            Optional[str]: The contents of the YAML file, or None if an error occurred.
        """
        try:
            with open(filepath, "r") as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: The file {filepath} does not exist.")
            return None
        except IOError as e:
            print(f"Error reading file {filepath}: {e}")
            return None

    def extract_endpoints(self, note: str) -> Dict[str, list]:
        """
        Extracts API endpoints from a note using regular expressions.

        Args:
            note (str): The note containing endpoint definitions.

        Returns:
            Dict[str, list]: A dictionary with endpoints as keys and HTTP methods as values.
        """
        required_endpoints = {}
        pattern = r"(\d+\.\s+GET)\s(/[\w{}]+)"
        matches = re.findall(pattern, note)

        for match in matches:
            method, endpoint = match
            method = method.split()[1]
            if endpoint in required_endpoints:
                if method not in required_endpoints[endpoint]:
                    required_endpoints[endpoint].append(method)
            else:
                required_endpoints[endpoint] = [method]

        return required_endpoints

    def extract_keys(self, key: str, value: Any, properties_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts and formats the keys and values from a dictionary to generate OpenAPI properties.

        Args:
            key (str): The key in the dictionary.
            value (Any): The value associated with the key.
            properties_dict (Dict[str, Any]): The dictionary to store the extracted properties.

        Returns:
            Dict[str, Any]: The updated properties dictionary.
        """
        if key == "id":
            properties_dict[key] = {
                "type": str(type(value).__name__),
                "format": "uuid",
                "example": str(value),
            }
        else:
            properties_dict[key] = {"type": str(type(value).__name__), "example": str(value)}

        return properties_dict

    def evaluate_result(self, result: Any, prompt_history: Prompt) -> Any:
        """
        Evaluates the result using the LLM-based response analyzer.

        Args:
            result (Any): The result to evaluate.
            prompt_history (list): The history of prompts used in the evaluation.

        Returns:
            Any: The evaluation result from the LLM response analyzer.
        """
        llm_responses, status_code = self.response_analyzer.analyze_response(result, prompt_history)
        return llm_responses, status_code

    def extract_key_elements_of_response(self, raw_response: Any) -> str:
        status_code, headers, body = self.response_analyzer.parse_http_response(raw_response)
        return "Status Code: " + str(status_code) + "\nHeaders:" + str(headers) + "\nBody" + str(body)

    def handle_response(self, response, completion, prompt_history, log, categorized_endpoints, move_type):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            response (str): The response to evaluate.
            completion (Completion): The completion object with tool call results.
            prompt_history (list): History of prompts and responses.
            log (Log): Logging object for console output.

        Returns:
            tuple: (bool, prompt_history, result, result_str) indicating if response is acceptable.
        """
        # Extract message and tool call information
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id

        if self.repeat_counter == 3:
            self.repeat_counter = 0
            self.prompt_helper.hint_for_next_round = f'Try this endpoint in the next round {next(self.common_endpoints)}'
            self.no_action_counter += 1
            return False, prompt_history, None, None

        if response.__class__.__name__ == "RecordNote":
            prompt_history.append(tool_message(response, tool_call_id))
            return False, prompt_history, None, None

        else:
            return self.handle_http_response(response, prompt_history, log, completion, message, categorized_endpoints,
                                             tool_call_id, move_type)

    def normalize_path(self, path):
        # Use regex to strip trailing digits
        return re.sub(r'\d+$', '', path)

    def check_path_variants(self, path, paths):
        # Normalize the paths
        normalized_paths = [self.normalize_path(path) for path in paths]

        # Count each normalized path
        path_counts = Counter(normalized_paths)

        # Extract paths that have more than one variant
        variants = {path: count for path, count in path_counts.items() if count > 1}
        if len(variants) != 0:
            return True
        return False

    def handle_http_response(self, response: Any, prompt_history: Any, log: Any, completion: Any, message: Any,
                             categorized_endpoints, tool_call_id, move_type) -> Any:
        if not response.action.__class__.__name__ == "RecordNote":
            if self.no_action_counter == 5:
                response.action.path = self.get_next_path(response.action.path)
                self.no_action_counter = 0
            else:
                response.action.path = self.adjust_path_if_necessary(response.action.path)
                if move_type == "exploit" and len(self.prompt_helper.get_instance_level_endpoints()) != 0:
                    exploit_endpoint = self.prompt_helper.get_instance_level_endpoint()

                    if exploit_endpoint != None:
                        response.action.path = exploit_endpoint
            # Add Authorization header if token is available
            if self.token != "":
                response.action.headers = {"Authorization": f"Bearer {self.token}"}
        # Convert response to JSON and display it
        command = json.loads(pydantic_core.to_json(response).decode())
        log.console.print(Panel(json.dumps(command, indent=2), title="assistant"))


        # Execute the command and parse the result
        with log.console.status("[bold green]Executing command..."):
            if response.__class__.__name__ == "RecordNote":
                print("HHHHHHHH")
            result = response.execute()
            self.query_counter += 1
            result_dict = self.extract_json(result)
            log.console.print(Panel(result, title="tool"))
        if not response.action.__class__.__name__ == "RecordNote":

            self.prompt_helper.tried_endpoints.append(response.action.path)

            # Parse HTTP status and request path
            result_str = self.parse_http_status_line(result)

            request_path = response.action.path

            # Check for missing action
            if "action" not in command:
                return False, prompt_history, response, completion

            # Determine if the response is successful
            is_successful = result_str.startswith("200")
            prompt_history.append(message)
            self.last_path = request_path

            # Determine if the request path is correct and set the status message
            if is_successful:
                if request_path.split("?")[0] not in self.prompt_helper.found_endpoints:
                    # Update current step and add to found endpoints
                    self.prompt_helper.found_endpoints.append(request_path.split("?")[0])
                status_message = f"{request_path} is a correct endpoint"
            else:
                # Handle unsuccessful paths and error message

                error_msg = result_dict.get("error", {}).get("message", "unknown error")
                print(f'ERROR MSG: {error_msg}')

                if result_str.startswith("400"):
                    status_message = f"{request_path} is a correct endpoint, but encountered an error: {error_msg}"

                    if error_msg not in self.prompt_helper.correct_endpoint_but_some_error.keys():
                        self.prompt_helper.correct_endpoint_but_some_error[error_msg] = []
                    self.prompt_helper.correct_endpoint_but_some_error[error_msg].append(request_path)
                    self.prompt_helper.hint_for_next_round = error_msg

                else:
                    self.prompt_helper.unsuccessful_paths.append(request_path)
                    status_message = f"{request_path} is not a correct endpoint; Reason: {error_msg}"

            self.adjust_counter(categorized_endpoints)

            prompt_history.append(tool_message(status_message, tool_call_id))
            print(f'QUERY COUNT: {self.query_counter}')
        else:
            prompt_history.append(tool_message(result, tool_call_id))
            is_successful = False
            result_str = result[:20]

        return is_successful, prompt_history, result, result_str

    def get_next_key(self, current_key, dictionary):
        keys = list(dictionary.keys())  # Convert keys to a list
        try:
            current_index = keys.index(current_key)  # Find the index of the current key
            return keys[current_index + 1]  # Return the next key
        except (ValueError, IndexError):
            return None  # Return None if the current key is not found or there is no next key

    def extract_json(self, response: str) -> dict:
        try:
            # Find the start of the JSON body by locating the first '{' character
            json_start = response.index('{')
            # Extract the JSON part of the response
            json_data = response[json_start:]
            # Convert the JSON string to a dictionary
            data_dict = json.loads(json_data)
            return data_dict
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Error extracting JSON: {e}")
            return {}

    def generate_variants_of_found_endpoints(self, type_of_variant):
        for endpoint in self.prompt_helper.found_endpoints:
            if endpoint + "/1" in self.variants_of_found_endpoints:
                self.variants_of_found_endpoints.remove(endpoint + "/1")
            if "id" not in endpoint and endpoint + "/{id}" not in self.prompt_helper.found_endpoints and endpoint.endswith(
                    's'):
                self.variants_of_found_endpoints.append(endpoint + "/1")
            if "/1" not in self.variants_of_found_endpoints or self.prompt_helper.found_endpoints:
                self.variants_of_found_endpoints.append("/1")

    def get_next_path(self, path):
        counter = 0
        if self.prompt_helper.current_step >= 6:
            return self.create_common_query_for_endpoint(path)
        try:

            new_path = next(self.common_endpoints_categorized[self.prompt_helper.current_step])
            while not new_path in self.prompt_helper.found_endpoints or not new_path in self.prompt_helper.unsuccessful_paths:
                new_path = next(self.common_endpoints_categorized[self.prompt_helper.current_step])
                counter = counter + 1
                if counter >= 6:
                    return new_path

            return new_path
        except StopIteration:
            return path

    def adjust_path_if_necessary(self, path):
        # Initial processing and checks
        parts = [part for part in path.split("/") if part]
        pattern_replaced_path = self.pattern_matcher.replace_according_to_pattern(path)

        if not path.startswith("/"):
            path = "/" + path
        # Check for no action and reset if needed
        if self.no_action_counter == 5:
            path = self.get_next_path(path)
            self.no_action_counter = 0
        else:

            # Specific logic based on current_step and the structure of parts
            if parts:
                root_path = '/' + parts[0]
                if self.prompt_helper.current_step == 1:
                    if len(parts) != 1:
                        if (root_path not in self.prompt_helper.found_endpoints and root_path not in self.prompt_helper.unsuccessful_paths):
                            self.save_endpoint(path)
                            path = root_path
                        else:
                            self.save_endpoint(path)
                            path = self.get_next_path(path)


                    else:
                            self.save_endpoint(path)
                            if path in self.prompt_helper.found_endpoints or path in self.prompt_helper.unsuccessful_paths or path == self.last_path:
                                path = self.get_next_path(path)

                elif self.prompt_helper.current_step == 2 and len(parts) != 2:
                    if path in self.prompt_helper.unsuccessful_paths:
                        path = self.prompt_helper.get_instance_level_endpoint()
                    elif path in self.prompt_helper.found_endpoints and len(parts) == 1:
                        path = path + '/1'
                    else:
                        path = self.prompt_helper.get_instance_level_endpoint()

                    print(f'PATH: {path}')
                elif self.prompt_helper.current_step == 6 and not "?" in path:
                    path = self.create_common_query_for_endpoint(path)

                # Check if the path is already handled or matches known patterns
                elif (path == self.last_path or
                    path in self.prompt_helper.unsuccessful_paths or
                    path in self.prompt_helper.found_endpoints and self.prompt_helper.current_step != 6 or
                    pattern_replaced_path in self.prompt_helper.found_endpoints or
                    pattern_replaced_path in self.prompt_helper.unsuccessful_paths
                    and self.prompt_helper.current_step != 2):

                    path = self.get_saved_endpoint()
        if path == None:
            path = self.get_next_path(path)

            # Replacement logic for dynamic paths containing placeholders

        if "{id}" in path:
            path = path.replace("{id}", "1")

        print(f'PATH: {path}')

        if self.name.__contains__("OWASP API"):
            return path.capitalize()

        return path

    def save_endpoint(self, path):
        parts = [part for part in path.split("/") if part]
        if len(parts) not in self.saved_endpoints.keys():
            self.saved_endpoints[len(parts)] = []
        self.saved_endpoints[len(parts)].append(path)

    def get_saved_endpoint(self):
        # First check if there are any saved endpoints for the current step
        if self.prompt_helper.current_step in self.saved_endpoints and self.saved_endpoints[
            self.prompt_helper.current_step]:
            # Get the first endpoint in the list for the current step
            saved_endpoint = self.saved_endpoints[self.prompt_helper.current_step][0]
            saved_endpoint = saved_endpoint.replace("{id}", "1")

            # Check if this endpoint has not been found or unsuccessfully tried
            if saved_endpoint not in self.prompt_helper.found_endpoints and saved_endpoint not in self.prompt_helper.unsuccessful_paths:
                # If it is a valid endpoint, delete it from saved endpoints to avoid reuse
                del self.saved_endpoints[self.prompt_helper.current_step][0]
                if not saved_endpoint.endswith("s") and not saved_endpoint.endswith("1"):
                    saved_endpoint = saved_endpoint + "s"
                return saved_endpoint

        # Return None or raise an exception if no valid endpoint is found
        return None

    def adjust_counter(self, categorized_endpoints):
        # Helper function to handle the increment and reset actions
        def update_step_and_category():
            self.prompt_helper.current_step += 1
            self.prompt_helper.current_category = self.get_next_key(self.prompt_helper.current_category,
                                                                    categorized_endpoints)
            self.query_counter = 0

        # Check for step-specific conditions or query count thresholds
        if ( self.prompt_helper.current_step == 1 and self.query_counter > 150):
            update_step_and_category()
        elif self.prompt_helper.current_step == 2 and not self.prompt_helper.get_instance_level_endpoints():
            update_step_and_category()
        elif self.prompt_helper.current_step > 2 and self.query_counter > 30:
            update_step_and_category()
        elif self.prompt_helper.current_step == 7 and not self.prompt_helper.get_root_level_endpoints():
            update_step_and_category()

    def create_common_query_for_endpoint(self, base_url, sample_size=2):
        """
           Constructs a complete URL with query parameters for an API request.

           Args:
               base_url (str): The base URL of the API endpoint.
               params (dict): A dictionary of parameters where keys are parameter names and values are the values for those parameters.

           Returns:
               str: The full URL with appended query parameters.
           """

        # Define common query parameters
        common_query_params = [
            "page", "limit", "sort", "filter", "search", "api_key", "access_token",
            "callback", "fields", "expand", "since", "until", "status", "lang",
            "locale", "region", "embed", "version", "format"
        ]

        # Sample dictionary of parameters for demonstration
        full_params = {
            "page": 2,
            "limit": 10,
            "sort": "date_desc",
            "filter": "status:active",
            "search": "example query",
            "api_key": "YourAPIKeyHere",
            "access_token": "YourAccessToken",
            "callback": "myFunction",
            "fields": "id,name,status",
            "expand": "details,owner",
            "since": "2020-01-01T00:00:00Z",
            "until": "2022-01-01T00:00:00Z",
            "status": "active",
            "lang": "en",
            "locale": "en_US",
            "region": "North America",
            "embed": "true",
            "version": "1.0",
            "format": "json"
        }

        # Randomly pick a subset of parameters from the list
        sampled_params_keys = random.sample(common_query_params, min(sample_size, len(common_query_params)))

        # Filter the full_params to include only the sampled parameters
        sampled_params = {key: full_params[key] for key in sampled_params_keys if key in full_params}

        # Encode the parameters into a query string
        query_string = urlencode(sampled_params)
        if base_url == None:
            instance_level_endpoints = self.prompt_helper.get_instance_level_endpoints()
            base_url = random.choice(instance_level_endpoints)
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        return f"{base_url}?{query_string}"
