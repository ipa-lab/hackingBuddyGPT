import os
from collections import defaultdict
from datetime import datetime

import pydantic_core
import yaml
from rich.panel import Panel

from hackingBuddyGPT.capabilities.yamlFile import YAMLFile
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

    def __init__(self, llm_handler: LLMHandler, response_handler: ResponseHandler, strategy: PromptStrategy,):
        """
        Initializes the handler with a template OpenAPI specification.

        Args:
            llm_handler (object): An instance of the LLM handler for interacting with the LLM.
            response_handler (object): An instance of the response handler for processing API responses.
            strategy (PromptStrategy): An instance of the PromptStrategy class.
        """
        self.response_handler = response_handler
        self.schemas = {}
        self.endpoint_methods = {}
        self.filename = f"openapi_spec_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.yaml"
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Generated API Documentation",
                "version": "1.0",
                "description": "Automatically generated description of the API.",
            },
            "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
            "endpoints": {},
            "components": {"schemas": {}},
        }
        self.llm_handler = llm_handler
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "openapi_spec", str(strategy).split(".")[1].lower())
        self.file = os.path.join(self.file_path, self.filename)
        self._capabilities = {"yaml": YAMLFile()}

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
        status_code, status_message = result_str.split(" ", 1)

        if request.__class__.__name__ == "RecordNote":  # TODO: check why isinstance does not work
            self.check_openapi_spec(resp)
            return list(self.openapi_spec["endpoints"].keys())

        if request.__class__.__name__ == "HTTPRequest":
            path = request.path
            method = request.method

            if not path or not method :
                return list(self.openapi_spec["endpoints"].keys())
            if "1" in path:
                path = path.replace("1", ":id")
            endpoint_methods = self.endpoint_methods
            endpoints = self.openapi_spec["endpoints"]

            # Extract the main part of the path for checking partial matches
            path_parts = path.split("/")
            main_path = path_parts[1] if len(path_parts) > 1 else ""

            # Initialize the path if it's not present and is valid
            if path not in endpoints and main_path:
                endpoints[path] = {}
                endpoint_methods[path] = []

            # Parse the response into OpenAPI example and reference
            example, reference, self.openapi_spec = self.response_handler.parse_http_response_to_openapi_example(
                self.openapi_spec, result, path, method
            )
            self.schemas = self.openapi_spec["components"]["schemas"]

            # Add example and reference to the method's responses if available
            if example or reference:
                endpoints[path][method.lower()] = {
                    "summary": f"{method} operation on {path}",
                    "responses": {
                        f"{status_code}": {
                            "description": status_message,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": reference},
                                    "examples": example
                                }
                            }
                        }
                    }
                }

                # Update endpoint methods for the path
                endpoint_methods[path].append(method)

                # Ensure uniqueness of methods for each path
                endpoint_methods[path] = list(set(endpoint_methods[path]))

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
        from hackingBuddyGPT.usecases.web_api_testing.utils.documentation.parsing.yaml_assistant import (
            YamlFileAssistant,
        )

        #yaml_file_assistant = YamlFileAssistant(self.file_path, self.llm_handler)
        #yaml_file_assistant.run(description)

    def _update_documentation(self, response, result,result_str, prompt_engineer):
        prompt_engineer.prompt_helper.found_endpoints = self.update_openapi_spec(response, result, result_str)
        self.write_openapi_to_yaml()
        prompt_engineer.prompt_helper.schemas = self.schemas

        http_methods_dict = defaultdict(list)
        for endpoint, methods in self.endpoint_methods.items():
            for method in methods:
                http_methods_dict[method].append(endpoint)

        prompt_engineer.prompt_helper.endpoint_found_methods = http_methods_dict
        prompt_engineer.prompt_helper.endpoint_methods = self.endpoint_methods
        return prompt_engineer

    def document_response(self, completion, response, log, prompt_history, prompt_engineer):
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        command = pydantic_core.to_json(response).decode()

        log.console.print(Panel(command, title="assistant"))
        prompt_history.append(message)

        with log.console.status("[bold green]Executing that command..."):
            result = response.execute()
            log.console.print(Panel(result[:30], title="tool"))
            result_str = self.response_handler.parse_http_status_line(result)
            prompt_history.append(tool_message(result_str, tool_call_id))

            invalid_flags = {"recorded"}
            if result_str not in invalid_flags or any(flag in result_str for flag in invalid_flags):
                prompt_engineer = self._update_documentation(response, result,result_str, prompt_engineer)

        return log, prompt_history, prompt_engineer

    def found_all_endpoints(self):
        if len(self.endpoint_methods.items()) < 10:
            return False
        else:
            return True
