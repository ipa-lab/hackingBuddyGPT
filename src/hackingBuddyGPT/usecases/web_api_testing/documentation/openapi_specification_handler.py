import os
import re
from collections import defaultdict
from datetime import datetime

import pydantic_core
import yaml
from rich.panel import Panel

from hackingBuddyGPT.capabilities.yamlFile import YAMLFile
from hackingBuddyGPT.usecases.web_api_testing.documentation.pattern_matcher import PatternMatcher
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.utils import tool_message


class OpenAPISpecificationHandler(object):
    """
    Handles the generation and updating of an OpenAPI specification document based on dynamic API responses.

    Attributes:
        response_handler (object): An instance of the response handler for processing API responses.
        schemas (dict): A dictionary to store API schemas.
        filename (str): The filename for the OpenAPI specification file.
        openapi_spec (dict): The OpenAPI specification document structure.
        llm_handler (object): An instance of the LLM handler for interacting with the LLM.
        api_key (str): The API key for accessing the LLM.
        file_path (str): The path to the directory where the OpenAPI specification file will be stored.
        file (str): The complete path to the OpenAPI specification file.
        _capabilities (dict): A dictionary to store capabilities related to YAML file handling.
    """

    def __init__(self, llm_handler: LLMHandler, response_handler: ResponseHandler, strategy: PromptStrategy, url: str,
                 description: str, name: str) -> None:
        """
        Initializes the handler with a template OpenAPI specification.

        Args:
            llm_handler (object): An instance of the LLM handler for interacting with the LLM.
            response_handler (object): An instance of the response handler for processing API responses.
            strategy (PromptStrategy): An instance of the PromptStrategy class.
        """
        self.unsuccessful_methods = {}
        self.response_handler = response_handler
        self.schemas = {}
        self.query_params = {}
        self.endpoint_methods = {}
        self.filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.yaml"
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Generated API Documentation {name}",
                "version": "1.0",
                "description": f"{description} + \nUrl:{url}",
            },
            "servers": [{"url": f"{url}"}],  # https://jsonplaceholder.typicode.com
            "endpoints": {},
            "components": {"schemas": {}},
        }
        self.llm_handler = llm_handler
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "openapi_spec", str(strategy).split(".")[1].lower(), name.lower())
        os.makedirs(self.file_path, exist_ok=True)
        self.file = os.path.join(self.file_path, self.filename)

        self._capabilities = {"yaml": YAMLFile()}
        self.unsuccessful_paths = []

        self.pattern_matcher = PatternMatcher()

    def is_partial_match(self, element, string_list):
        return any(element in string or string in element for string in string_list)

    def update_openapi_spec(self, resp, result, result_str):
        """
        Updates the OpenAPI specification based on the API response provided.

        Args:
            resp (object): The response object containing details like the path and method which should be documented.
            result (str): The result of the API call.
        """
        request = resp.action
        status_code, status_message = self.extract_status_code_and_message(result)

        if request.__class__.__name__ == "RecordNote":  # TODO: check why isinstance does not work
            # self.check_openapi_spec(resp)
            return list(self.openapi_spec["endpoints"].keys())

        if request.__class__.__name__ == "HTTPRequest":
            path = request.path
            method = request.method
            if "1" in path:
                path = path.replace("1", "{id}")
            path  = self.replace_crypto_with_id(path)
            if not path or not method or path == "/" or not path.startswith("/"):
                return list(self.openapi_spec["endpoints"].keys())

            # replace specific values with generic values for doc
            path = self.pattern_matcher.replace_according_to_pattern(path)
            print(f'Path:{path}')

            if path in self.unsuccessful_paths:
                return list(self.openapi_spec["endpoints"].keys())


            endpoint_methods = self.endpoint_methods
            endpoints = self.openapi_spec["endpoints"]

            # Extract the main part of the path for checking partial matches
            path_parts = path.split("/")
            main_path = path if len(path_parts) > 1 else ""

            # Initialize the path if it's not present and is valid
            if status_code.startswith("20"):
                if path not in endpoints and "?" not in path:
                    endpoints[path] = {}
                    endpoint_methods[path] = []

            unsuccessful_status_codes = ["400", "404", "500"]

            if path in endpoints and (status_code in unsuccessful_status_codes):
                self.unsuccessful_paths.append(path)
                if path in  self.unsuccessful_methods:
                    self.unsuccessful_methods[path] = []
                self.unsuccessful_methods[path].append(method)
                return list(self.openapi_spec["endpoints"].keys())

            # Parse the response into OpenAPI example and reference
            example, reference, self.openapi_spec = self.response_handler.parse_http_response_to_openapi_example(
                self.openapi_spec, result, path, method
            )
            self.schemas = self.openapi_spec["components"]["schemas"]

            # Check if the path exists in the dictionary and the method is not already defined for this path
            if path in endpoints and method.lower() not in endpoints[path]:
                # Create a new dictionary for this method if it doesn't exist
                endpoints[path][method.lower()] = {
                    "summary": f"{method} operation on {path}",
                    "responses": {
                        f"{status_code}": {
                            "description": status_message,
                            "content": {}
                        }
                    }
                }

                # Update endpoint methods for the path
                endpoint_methods[path].append(method)

                # Ensure uniqueness of methods for each path
                endpoint_methods[path] = list(set(endpoint_methods[path]))

            # Check if there's a need to add or update the 'content' based on the conditions provided
            if example or reference or status_message == "No Content":
                # Ensure the path and method exists and has the 'responses' structure
                if path in endpoints and method.lower() in endpoints[path] and \
                        f"{status_code}" in endpoints[path][method.lower()]["responses"]:
                    # Get the response content dictionary
                    response_content = endpoints[path][method.lower()]["responses"][f"{status_code}"]["content"]

                    # Assign a new structure to 'content' under the specific status code
                    response_content["application/json"] = {
                        "schema": {"$ref": reference},
                        "examples": example
                    }


            # Add query parameters to the OpenAPI path item object
            if path.__contains__('?'):
                query_params_dict = self.pattern_matcher.extract_query_params(path)
                if query_params_dict != {}:
                    if path not in endpoints.keys():
                        endpoints[path] = {}
                    if method.lower() not in  endpoints[path]:
                        endpoints[path][method.lower()] = {}
                    endpoints[path][method.lower()].setdefault('parameters', [])
                    print(f'query_params: {query_params_dict}')
                    print(f'query_params: {query_params_dict.items()}')
                    for param, value in query_params_dict.items():
                        param_entry = {
                            "name": param,
                            "in": "query",
                            "required": True,  # Change this as needed
                            "schema": {
                                "type": self.get_type(value)  # Adjust the type based on actual data type
                            }
                        }
                        endpoints[path][method.lower()]['parameters'].append(param_entry)
                        if path not in self.query_params.keys():
                            self.query_params[path] = []
                        self.query_params[path].append(param)


        return list(self.openapi_spec["endpoints"].keys())

    def write_openapi_to_yaml(self):
        """
        Writes the updated OpenAPI specification to a YAML file with a timestamped filename.
        """
        try:
            # Prepare data to be written to YAML
            openapi_data = {
                "openapi": self.openapi_spec["openapi"],
                "info": self.openapi_spec["info"],
                "servers": self.openapi_spec["servers"],
                "components": self.openapi_spec["components"],
                "paths": self.openapi_spec["endpoints"],
            }

            # Create directory if it doesn't exist and generate the timestamped filename
            os.makedirs(self.file_path, exist_ok=True)

            # Write to YAML file
            with open(self.file, "w") as yaml_file:
                yaml.dump(openapi_data, yaml_file, allow_unicode=True, default_flow_style=False)
            print(f"OpenAPI specification written to {self.filename}.")
        except Exception as e:
            raise Exception(f"Error writing YAML file: {e}") from e

    def check_openapi_spec(self, note):
        """
        Uses OpenAI's GPT model to generate a complete OpenAPI specification based on a natural language description.

        Args:
            note (object): The note object containing the description of the API.
        """
        description = self.response_handler.extract_description(note)

        # yaml_file_assistant = YamlFileAssistant(self.file_path, self.llm_handler)
        # yaml_file_assistant.run(description)

    def _update_documentation(self, response, result, result_str, prompt_engineer):
        endpoints = self.update_openapi_spec(response, result, result_str)
        if prompt_engineer.prompt_helper.found_endpoints != endpoints and endpoints != [] and len(endpoints) != 1:
            prompt_engineer.prompt_helper.found_endpoints = list(
                set(prompt_engineer.prompt_helper.found_endpoints + endpoints))
            self.write_openapi_to_yaml()
            prompt_engineer.prompt_helper.schemas = self.schemas

        http_methods_dict = defaultdict(list)
        for endpoint, methods in self.endpoint_methods.items():
            for method in methods:
                http_methods_dict[method].append(endpoint)

        prompt_engineer.prompt_helper.endpoint_found_methods = http_methods_dict
        prompt_engineer.prompt_helper.endpoint_methods = self.endpoint_methods
        prompt_engineer.prompt_helper.unsuccessful_paths = self.unsuccessful_paths
        prompt_engineer.prompt_helper.unsuccessful_methods = self.unsuccessful_methods
        return prompt_engineer

    def document_response(self, result, response, result_str, prompt_history, prompt_engineer):

        invalid_flags = {"recorded"}
        if result_str not in invalid_flags or any(flag in result_str for flag in invalid_flags):
            prompt_engineer = self._update_documentation(response, result, result_str, prompt_engineer)

        return prompt_history, prompt_engineer

    def found_all_endpoints(self):
        if len(self.endpoint_methods.items()) < 10:
            return False
        else:
            return True

    def get_type(self, value):
        def is_double(s):
            # Matches numbers like -123.456, +7.890, and excludes integers
            return re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", s) is not None

        if value.isdigit():
            return "integer"
        elif is_double(value):
            return "double"
        else:
            return "string"

    def extract_status_code_and_message(self, result):
        match = re.search(r"^HTTP/\d\.\d\s+(\d+)\s+(.*)", result, re.MULTILINE)
        if match:
            status_code = match.group(1)
            status_message = match.group(2).strip()
            return status_code, status_message
        else:
            return None, None

    def replace_crypto_with_id(self, path):

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