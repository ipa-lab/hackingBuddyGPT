import json
import re
from typing import Any, Dict, Optional, Tuple

from bs4 import BeautifulSoup

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.pentesting_information import (
    PenTestingInformation,
)
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer_with_llm import (
    ResponseAnalyzerWithLLM,
)
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Prompt


class ResponseHandler:
    """
    ResponseHandler is a class responsible for handling various types of responses from an LLM (Large Language Model).
    It processes prompts, parses HTTP responses, extracts examples, and handles OpenAPI specifications.

    Attributes:
        llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        pentesting_information (PenTestingInformation): An instance containing pentesting information.
        response_analyzer (ResponseAnalyzerWithLLM): An instance for analyzing responses with the LLM.
    """

    def __init__(self, llm_handler: LLMHandler) -> None:
        """
        Initializes the ResponseHandler with the specified LLM handler.

        Args:
            llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        """
        self.llm_handler = llm_handler
        self.pentesting_information = PenTestingInformation()
        self.response_analyzer = ResponseAnalyzerWithLLM(llm_handler=llm_handler)

    def get_response_for_prompt(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM's API and retrieves the response.

        Args:
            prompt (str): The prompt to be sent to the API.

        Returns:
            str: The response from the API.
        """
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        response, completion = self.llm_handler.call_llm(messages)
        response_text = response.execute()
        return response_text

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
            body_dict (Dict[str, Any]): The HTTP response body as a dictionary.
            path (str): The API path.

        Returns:
            Tuple[str, str, Dict[str, Any]]: A tuple containing the reference, object name, and updated OpenAPI specification.
        """
        object_name = path.split("/")[1].capitalize().rstrip("s")
        properties_dict = {}

        if len(body_dict) == 1:
            properties_dict["id"] = {"type": "int", "format": "uuid", "example": str(body_dict["id"])}
        else:
            for param in body_dict:
                if isinstance(body_dict, list):
                    for key, value in param.items():
                        properties_dict = self.extract_keys(key, value, properties_dict)
                    break
                else:
                    for key, value in body_dict.items():
                        properties_dict = self.extract_keys(key, value, properties_dict)

        object_dict = {"type": "object", "properties": properties_dict}

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
