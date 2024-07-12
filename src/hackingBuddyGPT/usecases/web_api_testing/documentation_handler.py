import json
import os
import re
from bs4 import BeautifulSoup
import openai
import pydantic_core
import yaml
from datetime import datetime

from hackingBuddyGPT.capabilities.yamlFile import YAMLFile


class DocumentationHandler:
    """Handles the generation and updating of an OpenAPI specification document based on dynamic API responses."""

    def __init__(self, llm_handler, response_handler):
        """Initializes the handler with a template OpenAPI specification."""
        self.response_handler = response_handler
        self.schemas = {}
        self.filename = f"openapi_spec_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.yaml"
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Generated API Documentation",
                "version": "1.0",
                "description": "Automatically generated description of the API."
            },
            "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
            "endpoints": {},
            "components": {"schemas": {}}
        }
        self.llm_handler = llm_handler
        self.api_key = llm_handler.llm.api_key
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "openapi_spec")
        self.file = os.path.join(self.file_path, self.filename)
        yamls = []
        self._capabilities = {
            "yaml": YAMLFile()
        }

    def update_openapi_spec(self, resp, result):
        """
        Updates the OpenAPI specification based on the API response provided.

        Args:
        - response: The response object containing details like the path and method which should be documented.
        """
        request = resp.action


        if request.__class__.__name__ == 'RecordNote':  # TODO check why isinstance does not work
            self.check_openapi_spec(resp)
        if request.__class__.__name__ == 'HTTPRequest':
            path = request.path
            method = request.method
            print(f'method:{method}')
            # Ensure that path and method are not None and method has no numeric characters
            if path and method:
                # Initialize the path if not already present
                if path not in self.openapi_spec['endpoints']:
                    self.openapi_spec['endpoints'][path] = {}
                # Update the method description within the path
                example, reference, self.openapi_spec = self.response_handler.parse_http_response_to_openapi_example(self.openapi_spec, result, path, method)
                if example != None or reference != None:
                    self.openapi_spec['endpoints'][path][method.lower()] = {
                    "summary": f"{method} operation on {path}",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": reference
                                    },
                                    "examples": example
                                }
                            }
                        }

                    }
                }



    def write_openapi_to_yaml(self):
        """Writes the updated OpenAPI specification to a YAML file with a timestamped filename."""
        try:
            # Prepare data to be written to YAML
            openapi_data = {
                "openapi": self.openapi_spec["openapi"],
                "info": self.openapi_spec["info"],
                "servers": self.openapi_spec["servers"],
                "components": self.openapi_spec["components"],
                "paths": self.openapi_spec["endpoints"]
            }

            # Create directory if it doesn't exist and generate the timestamped filename
            os.makedirs(self.file_path, exist_ok=True)

            # Write to YAML file
            with open(self.file, 'w') as yaml_file:
                yaml.dump(openapi_data, yaml_file, allow_unicode=True, default_flow_style=False)
            print(f"OpenAPI specification written to {self.filename}.")
        except Exception as e:
            raise Exception(f"Error writing YAML file: {e}")




    def check_openapi_spec(self, note):
        """
            Uses OpenAI's GPT model to generate a complete OpenAPI specification based on a natural language description.

            Parameters:
            - api_key: str. Your OpenAI API key.
            - file_path: str. Path to the YAML file to update.
            - description: str. A detailed description of the entire API.
            """
        description = self.response_handler.extract_description(note)
        from hackingBuddyGPT.usecases.web_api_testing.yaml_assistant import YamlFileAssistant
        yaml_file_assistant = YamlFileAssistant(self.file_path, self.llm_handler)
        yaml_file_assistant.run(description)

