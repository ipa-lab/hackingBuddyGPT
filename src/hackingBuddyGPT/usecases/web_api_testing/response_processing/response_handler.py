import json
import re
from itertools import cycle
from typing import Any, Dict, Optional, Tuple

import pydantic_core
from bs4 import BeautifulSoup
from rich.panel import Panel

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

    def __init__(self, llm_handler: LLMHandler, prompt_context: PromptContext, token: str,
                 prompt_helper: PromptGenerationHelper, pentesting_information: PenTestingInformation=None) -> None:
        """
        Initializes the ResponseHandler with the specified LLM handler.

        Args:
            llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        """
        self.llm_handler = llm_handler
        if prompt_context == PromptContext.PENTESTING:
            self.pentesting_information = pentesting_information
            self.response_analyzer = ResponseAnalyzerWithLLM(llm_handler=llm_handler, pentesting_info= pentesting_information)

        self.common_endpoints = cycle(
            ['/api', '/auth', '/users', '/products', '/orders', '/cart', '/checkout', '/payments', '/transactions',
             '/notifications', '/messages', '/files', '/admin', '/settings', '/status', '/health', '/healthcheck',
             '/info', '/docs', '/swagger', '/openapi', '/metrics', '/logs', '/analytics', '/search', '/feedback',
             '/support', '/profile', '/account', '/reports', '/dashboard', '/activity', '/subscriptions', '/webhooks',
             '/events', '/upload', '/download', '/images', '/videos', '/user/login', '/api/v1', '/api/v2',
             '/auth/login', '/auth/logout', '/auth/register', '/auth/refresh', '/users/{id}', '/users/me',
             '/users/profile', '/users/settings', '/products/{id}', '/products/search', '/orders/{id}',
             '/orders/history', '/cart/items', '/cart/checkout', '/checkout/confirm', '/payments/{id}',
             '/payments/methods', '/transactions/{id}', '/transactions/history', '/notifications/{id}',
             '/messages/{id}', '/messages/send', '/files/upload', '/files/{id}', '/admin/users', '/admin/settings',
             '/settings/preferences', '/search/results', '/feedback/{id}', '/support/tickets', '/profile/update',
             '/password/reset', '/password/change', '/account/delete', '/account/activate', '/account/deactivate',
             '/account/settings', '/account/preferences', '/reports/{id}', '/reports/download', '/dashboard/stats',
             '/activity/log', '/subscriptions/{id}', '/subscriptions/cancel', '/webhooks/{id}', '/events/{id}',
             '/images/{id}', '/videos/{id}', '/files/download/{id}', '/support/tickets/{id}'])
        self.query_counter = 0
        self.repeat_counter = 0
        self.token = token
        self.last_path = ""
        self.prompt_helper = prompt_helper

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
        llm_responses = self.response_analyzer.analyze_response(result, prompt_history)
        return llm_responses

    def extract_key_elements_of_response(self, raw_response: Any) -> str:
        status_code, headers, body = self.response_analyzer.parse_http_response(raw_response)
        return "Status Code: " + str(status_code) + "\nHeaders:" + str(headers) + "\nBody" + str(body)

    def handle_response(self, response, completion, prompt_history, log, categorized_endpoints):
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

        if self.repeat_counter == 5:
            self.repeat_counter = 0
            self.prompt_helper.hint_for_next_round = f'Try this endpoint in the next round {next(self.common_endpoints)}'

        if response.__class__.__name__ == "RecordNote":
            prompt_history.append(tool_message(response, tool_call_id))
            return False, prompt_history, None, None

        else:
            return self.handle_http_response(response, prompt_history, log, completion, message, categorized_endpoints,
                                             tool_call_id)

    def handle_http_response(self, response: Any, prompt_history: Any, log: Any, completion: Any, message: Any,
                             categorized_endpoints, tool_call_id) -> Any:
        parts = parts = [part for part in response.action.path.split("/") if part]
        if response.action.path == self.last_path or response.action.path in self.prompt_helper.unsuccessful_paths or response.action.path in self.prompt_helper.found_endpoints:
            self.prompt_helper.hint_for_next_round = f"DO not try this path {self.last_path}. You already tried this before!"
            self.repeat_counter += 1
            return False, prompt_history, None, None

        if self.prompt_helper.current_step == "instance_level" and len(parts) != 2:
            self.prompt_helper.hint_for_next_round = "Endpoint path has to consist of a resource + / + and id."
            return False, prompt_history, None, None

        # Add Authorization header if token is available
        if self.token != "":
            response.action.headers = {"Authorization": f"Bearer {self.token}"}

        # Convert response to JSON and display it
        command = json.loads(pydantic_core.to_json(response).decode())
        log.console.print(Panel(json.dumps(command, indent=2), title="assistant"))

        # Execute the command and parse the result
        with log.console.status("[bold green]Executing command..."):
            result = response.execute()
            self.query_counter += 1
            result_dict = self.extract_json(result)
            log.console.print(Panel(result, title="tool"))

        # Parse HTTP status and request path
        result_str = self.parse_http_status_line(result)
        request_path = command.get("action", {}).get("path")

        # Check for missing action
        if "action" not in command:
            return False, prompt_history, response, completion

        # Determine if the response is successful
        is_successful = result_str.startswith("200")
        prompt_history.append(message)
        self.last_path = request_path

        # Determine if the request path is correct and set the status message
        if is_successful:
            # Update current step and add to found endpoints
            self.prompt_helper.found_endpoints.append(request_path)
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

        if self.query_counter > 30:
            self.prompt_helper.current_step += 1
            self.prompt_helper.current_category = self.get_next_key(self.prompt_helper.current_category,
                                                                    categorized_endpoints)
            self.query_counter = 0

        prompt_history.append(tool_message(status_message, tool_call_id))

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
