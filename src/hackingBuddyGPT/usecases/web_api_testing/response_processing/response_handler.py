import copy
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

from hackingBuddyGPT.utils.web_api.pattern_matcher import PatternMatcher
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.information import (
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
        self.no_new_endpoint_counter = 0
        self.all_query_combinations = []
        self.llm_handler = llm_handler
        self.no_action_counter = 0
        if prompt_context == PromptContext.PENTESTING:
            self.pentesting_information = pentesting_information

        self.common_endpoints = ['autocomplete', '/api', '/auth', '/login', '/admin', '/register', '/users', '/photos', '/images',
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
        self.common_endpoints_categorized_cycle, self.common_endpoints_categorized = self.categorize_endpoints()
        self.query_counter = 0
        self.repeat_counter = 0
        self.variants_of_found_endpoints = []
        self.name = config.get("name")
        self.token = config.get("token")
        self.last_path = ""
        self.prompt_helper = prompt_helper
        self.pattern_matcher = PatternMatcher()
        self.saved_endpoints = {}
        self.response_analyzer = None

    def set_response_analyzer(self, response_analyzer: ResponseAnalyzerWithLLM) -> None:
        self.response_analyzer = response_analyzer

    def categorize_endpoints(self) :
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
        }, {
        1: root_level,
        2: single_parameter,
        3: subresource,
        4: related_resource,
        5: multi_level_resource,
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
        old_body_dict = copy.deepcopy(body_dict)

        if len(body_dict) == 1 and "data" not in body_dict:
            entry_dict["id"] = body_dict
            self.llm_handler._add_created_object(entry_dict, object_name)
        else:
            if "data" in body_dict:
                body_dict = body_dict["data"]
                if isinstance(body_dict, list) and len(body_dict) > 0:
                    body_dict = body_dict[0]
                    if isinstance(body_dict, list):
                        for entry in body_dict:
                            key = entry.get("title") or entry.get("name") or entry.get("id")
                            entry_dict[key] = {"value": entry}
                            self.llm_handler._add_created_object(entry_dict[key], object_name)
                            if len(entry_dict) > 3:
                                break


            if isinstance(body_dict, list) and len(body_dict) > 0:
                body_dict = body_dict[0]
                if isinstance(body_dict, list):

                    for entry in body_dict:
                        key = entry.get("title") or entry.get("name") or entry.get("id")
                        entry_dict[key] = entry
                        self.llm_handler._add_created_object(entry_dict[key], object_name)
                        if len(entry_dict) > 3:
                            break
            else:
                if isinstance(body_dict, list) and len(body_dict) == 0:
                    entry_dict = ""
                elif isinstance(body_dict, dict) and "data" in body_dict.keys():
                    entry_dict = body_dict["data"]
                    if isinstance(entry_dict, list) and len(entry_dict) > 0:
                        entry_dict = entry_dict[0]
                else:
                    entry_dict= body_dict
                self.llm_handler._add_created_object(entry_dict, object_name)
        if isinstance(old_body_dict, dict) and len(old_body_dict.keys()) > 0 and "data" in old_body_dict.keys() and isinstance(old_body_dict, dict) \
                and isinstance(entry_dict, dict):
            old_body_dict.pop("data")
            entry_dict = {**entry_dict, **old_body_dict}


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

    def evaluate_result(self, result: Any, prompt_history: Prompt, analysis_context: Any) -> Any:
        """
        Evaluates the result using the LLM-based response analyzer.

        Args:
            result (Any): The result to evaluate.
            prompt_history (list): The history of prompts used in the evaluation.

        Returns:
            Any: The evaluation result from the LLM response analyzer.
        """
        self.response_analyzer._prompt_helper = self.prompt_helper
        llm_responses, status_code = self.response_analyzer.analyze_response(result, prompt_history, analysis_context)
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
        if "undefined" in response.action.path :
            response.action.path = response.action.path.replace("undefined", "1")
        if "Id" in response.action.path:
            path = response.action.path.split("/")
            if len(path) > 2:
                response.action.path = f"/{path[0]}/1/{path[2]}"
            else:
                response.action.path = f"/{path[0]}/1"




        if self.repeat_counter == 3:
            self.repeat_counter = 0
            if self.prompt_helper.current_step == 2:
                adjusted_path = self.adjust_path_if_necessary(response.action.path)
                self.prompt_helper.hint_for_next_round = f'Try this endpoint in the next round {adjusted_path}'
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

        response = self.adjust_path(response, move_type)
        # Add Authorization header if token is available
        if self.token:
                response.action.headers = {"Authorization": f"Bearer {self.token}"}
        if self.name.__contains__("ballardtide"):
                response.action.headers = {"Authorization": f"{self.token}"}

        # Convert response to JSON and display it
        command = json.loads(pydantic_core.to_json(response).decode())
        log.console.print(Panel(json.dumps(command, indent=2), title="assistant"))

        # Execute the command and parse the result
        with log.console.status("[bold green]Executing command..."):


            result = response.execute()
            self.query_counter += 1
            result_dict = self.extract_json(result)
            log.console.print(Panel(result, title="tool"))
            if "Could not request" in result:
                return False, prompt_history, result, ""

        if response.action.__class__.__name__ != "RecordNote":
            self.prompt_helper.tried_endpoints.append(response.action.path)

            # Parse HTTP status and request path
            result_str = self.parse_http_status_line(result)
            request_path = response.action.path

            if "action" not in command:
                return False, prompt_history, response, completion

            # Check response success
            is_successful = result_str.startswith("200")
            msg = {"role": message.role, "content": message.content, "tool_calls": message.tool_calls}
            prompt_history.append(msg)
            self.last_path = request_path

            status_message = self.check_if_successful(is_successful, request_path, result_dict, result_str, categorized_endpoints)
            log.console.print(Panel(status_message, title="system"))

            prompt_history.append(tool_message(status_message, tool_call_id))

        else:
            prompt_history.append(tool_message(result, tool_call_id))
        is_successful = False
        result_str = result[:20]

        return is_successful, prompt_history, result, result_str

    def extract_params(self, url):

        params = re.findall(r'(\w+)=([^&]*)', url)
        extracted_params = {key: value for key, value in params}

        return extracted_params

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
            new_path = self.create_common_query_for_endpoint(path)
            if path == "params":
                return path
            return new_path
        try:

            new_path = next(self.common_endpoints_categorized_cycle[self.prompt_helper.current_step])
            while not new_path in self.prompt_helper.found_endpoints or not new_path in self.prompt_helper.unsuccessful_paths:
                new_path = next(self.common_endpoints_categorized_cycle[self.prompt_helper.current_step])
                counter = counter + 1
                if counter >= 6:
                    return new_path

            return new_path
        except StopIteration:
            return path


    def finalize_path(self, path: str) -> str:
            """
            Final processing on the path before returning:
              - Replace any '{id}' with '1'
              - Then ALWAYS replace '1' with 'bitcoin' (no more 'if "Coin" in self.name')
              - If "OWASP API" in self.name, capitalize the path
            """
            # Replace {id} with '1'
            # Unconditionally replace '1' with 'bitcoin'

            if path is None:
                l = self.common_endpoints_categorized[self.prompt_helper.current_step]
                return random.choice(l)
            if ("Coin" in self.name or "gbif" in self.name)and self.prompt_helper.current_step == 2:
                id = self.prompt_helper.get_possible_id_for_instance_level_ep(path)
                if id:
                    path = path.replace("1", f"{id}")
            else:
                path = path.replace("{id}", "1")

            # Keep the OWASP API naming convention if needed
            if "OWASP API" in self.name:
                path = path.capitalize()

            return path

    def adjust_path_if_necessary(self, path: str) -> str:
            """
            Adjusts the given path based on the current step in self.prompt_helper and certain conditions.
            Always replaces '1' with 'bitcoin', no matter what self.name is.
            """
            # Ensure path starts with a slash
            if not path.startswith("/"):
                path = "/" + path

            parts = [part for part in path.split("/") if part]
            pattern_replaced_path = self.pattern_matcher.replace_according_to_pattern(path)

            # Reset logic
            if self.no_action_counter == 5:
                self.no_action_counter = 0
                # Return next path (finalize it)
                return self.finalize_path(self.get_next_path(path))

            if parts:
                root_path = '/' + parts[0]

                if self.prompt_helper.current_step == 1:
                    if len(parts) > 1:
                        if root_path not in (
                                self.prompt_helper.found_endpoints or self.prompt_helper.unsuccessful_paths):
                            self.save_endpoint(path)
                            return self.finalize_path(root_path)
                        else:
                            self.save_endpoint(path)
                            return self.finalize_path(self.get_next_path(path))
                    else:
                        # Single-part path
                        if (path in self.prompt_helper.found_endpoints or
                                path in self.prompt_helper.unsuccessful_paths or
                                path == self.last_path):
                            return self.finalize_path(self.get_next_path(path))

                elif self.prompt_helper.current_step == 2:
                    if len(parts) != 2:
                        if path in self.prompt_helper.unsuccessful_paths:
                            ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                            return self.finalize_path(ep)

                        if path in self.prompt_helper.found_endpoints and len(parts) == 1:
                            if "Coin" in self.name or "gbif" in self.name:
                                id =  self.prompt_helper.get_possible_id_for_instance_level_ep(path)
                                if id:
                                    path = path.replace("1", f"{id}")
                                    return self.finalize_path(path)
                            # Append /1 -> becomes /bitcoin after finalize_path
                            return self.finalize_path(f"{path}/1")

                        ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                        return self.finalize_path(ep)

                elif self.prompt_helper.current_step == 3:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_sub_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints, self.name
                        )
                        return self.finalize_path(ep)

                    ep = self.prompt_helper._get_sub_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif self.prompt_helper.current_step == 4:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_related_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints,
                            self.name
                        )
                        return self.finalize_path(ep)

                    ep = self.prompt_helper._get_related_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif self.prompt_helper.current_step == 5:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_multi_level_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints,
                            self.name
                        )
                    else:
                        ep = self.prompt_helper._get_multi_level_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif (self.prompt_helper.current_step == 6 and
                      "?" not in path):
                    new_path = self.create_common_query_for_endpoint(path)
                    # If "no params", keep original path, else use new_path
                    return self.finalize_path(path if new_path == "no params" else new_path)

                # Already-handled paths
                if (path in {self.last_path,
                             *self.prompt_helper.unsuccessful_paths,
                             *self.prompt_helper.found_endpoints}
                        and self.prompt_helper.current_step != 6):
                    return self.finalize_path(random.choice(self.common_endpoints))

                # Pattern-based check
                if (pattern_replaced_path in self.prompt_helper.found_endpoints or
                    pattern_replaced_path in self.prompt_helper.unsuccessful_paths) and self.prompt_helper.current_step != 2:
                    return self.finalize_path(random.choice(self.common_endpoints))

            else:
                # No parts
                if self.prompt_helper.current_step == 1:
                    root_level_endpoints = self.prompt_helper._get_root_level_endpoints()
                    chosen = root_level_endpoints[0] if root_level_endpoints else self.get_next_path(path)
                    return self.finalize_path(chosen)

                if self.prompt_helper.current_step == 2:
                    ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                    return self.finalize_path(ep)

            # If none of the above conditions matched, we finalize the path or get_next_path
            if path:
                return self.finalize_path(path)
            return self.finalize_path(self.get_next_path(path))



    def save_endpoint(self, path):

        parts = [part.strip() for part in path.split("/") if part.strip()]
        if len(parts) not in self.saved_endpoints.keys():
            self.saved_endpoints[len(parts)] = []
        if path not in self.saved_endpoints[len(parts)]:
            self.saved_endpoints[len(parts)].append(path)
        if path not in self.prompt_helper.saved_endpoints:
            self.prompt_helper.saved_endpoints.append(path)

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
            if self.prompt_helper.current_step != 6:
                self.prompt_helper.current_step += 1
                self.prompt_helper.current_category = self.get_next_key(self.prompt_helper.current_category,
                                                                    categorized_endpoints)
                self.query_counter = 0

        # Check for step-specific conditions or query count thresholds
        if (self.prompt_helper.current_step == 1 and self.query_counter > 150):
            update_step_and_category()
        elif self.prompt_helper.current_step == 2 and not self.prompt_helper._get_instance_level_endpoints(self.name):
            update_step_and_category()
        elif self.prompt_helper.current_step > 2 and self.query_counter > 30:
            update_step_and_category()
        elif self.prompt_helper.current_step == 7 and not self.prompt_helper._get_root_level_endpoints(self.name):
            update_step_and_category()

    def create_common_query_for_endpoint(self, endpoint):
        """
        Constructs complete URLs with one query parameter for each API endpoint.


        Returns:
            list: A list of full URLs with appended query parameters.
        """

        endpoint = endpoint + "?"
        # Define common query parameters
        common_query_params = [
            "page", "limit", "sort", "filter", "search", "api_key", "access_token",
            "callback", "fields", "expand", "since", "until", "status", "lang",
            "locale", "region", "embed", "version", "format", "username"
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
            "format": "json",
            "username": "test"
        }

        urls_with_params = []

        # Iterate through all found endpoints
        # Pick one random parameter from the common query params
        random_param_key = random.choice(common_query_params)

        # Check if the selected key is in the full_params
        if random_param_key in full_params:
            sampled_params = {random_param_key: full_params[random_param_key]}
        else:
            sampled_params = {}

        # Encode the parameters into a query string
        query_string = urlencode(sampled_params)

        # Ensure the endpoint doesn't end with a slash
        if endpoint.endswith('/') or endpoint.endswith("?"):
            endpoint = endpoint[:-1]

        # Construct the full URL with the query parameter
        full_url = f"{endpoint}?{query_string}"
        urls_with_params.append(full_url)
        if endpoint in self.prompt_helper.query_endpoints_params.keys():
            if random_param_key not in self.prompt_helper.query_endpoints_params[endpoint]:
                if random_param_key not in self.prompt_helper.tried_endpoints_with_params[endpoint]:
                    return full_url

        if urls_with_params == None:
            return "no params"
        return random.choice(urls_with_params)

    def adjust_path(self, response, move_type):
            """
            Adjusts the response action path based on current step, unsuccessful paths, and move type.

            Args:
                response (Any): The HTTP response object containing the action and path.
                move_type (str): The type of move (e.g., 'exploit') influencing path adjustment.

            Returns:
                Any: The updated response object with an adjusted path.
            """
            old_path = response.action.path

            if "?" not in response.action.path and self.prompt_helper.current_step == 6:
                if response.action.path not in self.prompt_helper.saved_endpoints:
                    if response.action.query is not None:
                        return response
            # Process action if it's not RecordNote
            if response.action.__class__.__name__ != "RecordNote":
                if self.prompt_helper.current_step == 6 :
                    response.action.path = self.create_common_query_for_endpoint(response.action.path)

                if response.action.path in self.prompt_helper.unsuccessful_paths:
                    self.repeat_counter += 1

                if self.no_action_counter == 5:
                    response.action.path = self.get_next_path(response.action.path)
                    self.no_action_counter = 0
                parts = response.action.path.split("/")
                len_path = len([part.strip() for part in parts if part.strip()])
                if self.prompt_helper.current_step == 2:
                    if len_path  <2 or len_path > 2 or response.action.path  in self.prompt_helper.unsuccessful_paths:
                        id = self.prompt_helper.get_possible_id_for_instance_level_ep(parts[0])
                        if id:
                            response.action.path = parts[0] + f"/{id}"
                else:
                    if self.prompt_helper.current_step != 6 and not response.action.path.endswith("?"):
                        adjusted_path = self.adjust_path_if_necessary(response.action.path)
                        if adjusted_path != None:
                            response.action.path = adjusted_path

                        if move_type == "exploit" and self.repeat_counter == 3:
                            if len(self.prompt_helper.endpoints_to_try) != 0:
                                exploit_endpoint = self.prompt_helper.endpoints_to_try[0]
                                response.action.path = self.create_common_query_for_endpoint(exploit_endpoint)
                            else:
                                exploit_endpoint = self.prompt_helper._get_instance_level_endpoint(self.name)
                                self.repeat_counter = 0

                                if exploit_endpoint and response.action.path not in self.prompt_helper._get_instance_level_endpoints(self.name):
                                    response.action.path = exploit_endpoint
            if move_type != "exploit":
                response.action.method = "GET"

            if response.action.path == None:
                response.action.path = old_path

            return response

    def check_if_successful(self, is_successful, request_path, result_dict, result_str, categorized_endpoints):
        self.prompt_helper.new_endpoint_found = False
        if is_successful:
            self.prompt_helper.new_endpoint_found =True
            if "?" in request_path and request_path not in self.prompt_helper.found_query_endpoints:
                self.prompt_helper.found_query_endpoints.append(request_path)
            ep = request_path.split("?")[0]
            if ep in self.prompt_helper.endpoints_to_try:
                self.prompt_helper.endpoints_to_try.remove(ep)
            if ep in self.saved_endpoints:
                self.saved_endpoints[1].remove(ep)
            if ep in self.prompt_helper.saved_endpoints:
                self.prompt_helper.saved_endpoints.remove(ep)
            if ep not in self.prompt_helper.found_endpoints:
                self.prompt_helper.found_endpoints.append(ep)

            self.prompt_helper.query_endpoints_params.setdefault(ep, [])
            self.prompt_helper.tried_endpoints_with_params.setdefault(ep, [])
           # ep = self.check_if_crypto(ep)
            if ep not in self.prompt_helper.found_endpoints:
                if "?" not in ep and ep not in self.prompt_helper.found_endpoints:
                    self.prompt_helper.found_endpoints.append(ep)
                if "?" in ep and ep not in self.prompt_helper.found_query_endpoints:
                    self.prompt_helper.found_query_endpoints.append(ep)

            for key in self.extract_params(request_path):
                if ep not in self.prompt_helper.query_endpoints_params:
                    self.prompt_helper.query_endpoints_params[ep] = []
                if ep not  in self.prompt_helper.tried_endpoints_with_params:
                    self.prompt_helper.tried_endpoints_with_params[ep] = []
                self.prompt_helper.query_endpoints_params[ep].append(key)
                self.prompt_helper.tried_endpoints_with_params[ep].append(key)

            status_message = f"{request_path} is a correct endpoint"
            self.no_new_endpoint_counter= 0
        else:
            error_msg = result_dict.get("error", {}).get("message", "unknown error") if isinstance(
                result_dict.get("error", {}), dict) else result_dict.get("error", "unknown error")
            self.no_new_endpoint_counter +=1
            if error_msg == "unknown error" and (result_str.startswith("4") or result_str.startswith("5")):
                error_msg = result_str

            if result_str.startswith("400") or result_str.startswith("401") or result_str.startswith("403"):
                status_message = f"{request_path} is a correct endpoint, but encountered an error: {error_msg}"
                self.prompt_helper.endpoints_to_try.append(request_path)
                self.prompt_helper.bad_request_endpoints.append(request_path)
                self.save_endpoint(request_path)
                if request_path not in self.prompt_helper.saved_endpoints:
                    self.prompt_helper.saved_endpoints.append(request_path)

                if error_msg not in self.prompt_helper.correct_endpoint_but_some_error:
                    self.prompt_helper.correct_endpoint_but_some_error[error_msg] = []
                self.prompt_helper.correct_endpoint_but_some_error[error_msg].append(request_path)
            else:
                self.prompt_helper.unsuccessful_paths.append(request_path)
                status_message = f"{request_path} is not a correct endpoint; Reason: {error_msg}"

            ep = request_path.split("?")[0]
            self.prompt_helper.tried_endpoints_with_params.setdefault(ep, [])
            for key in self.extract_params(request_path):
                self.prompt_helper.tried_endpoints_with_params[ep].append(key)

       # self.adjust_counter(categorized_endpoints)

        return status_message

    def check_if_crypto(self, path):

        # Default list of cryptos to detect
        cryptos = ["bitcoin", "ethereum", "litecoin", "dogecoin",
                       "cardano", "solana"]

        # Convert to lowercase for the match, but preserve the original path for reconstruction if you prefer
        lower_path = path.lower()


        for crypto in cryptos:
            if crypto in lower_path:
                # Example approach: split by '/' and replace the segment that matches crypto
                parts = path.split('/')
                replaced_any = False
                for i, segment in enumerate(parts):
                    if segment.lower() == crypto:
                        parts[i] = "{id}"
                        if segment.lower() == crypto:
                            parts[i] = "{id}"
                            replaced_any = True
                            if replaced_any:
                                return "/".join(parts)


        return path