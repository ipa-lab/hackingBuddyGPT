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

    def __init__(self, llm_handler):
        """Initializes the handler with a template OpenAPI specification."""
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
            # Ensure that path and method are not None and method has no numeric characters
            if path and method and not any(char.isdigit() for char in path):
                # Initialize the path if not already present
                if path not in self.openapi_spec['endpoints']:
                    self.openapi_spec['endpoints'][path] = {}
                # Update the method description within the path
                example, reference = self.parse_http_response_to_openapi_example(result, path)
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

    def extract_response_example(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the JavaScript example code
        example_code = soup.find('code', {'id': 'example'})
        if example_code:
            example_text = example_code.get_text()
        else:
            return None

        # Extract the result placeholder for the response
        result_code = soup.find('code', {'id': 'result'})
        if result_code:
            result_text = result_code.get_text()
        else:
            return None

        # Format the response example
        return json.loads(result_text)

    def parse_http_response_to_openapi_example(self, http_response, path):
        # Extract headers and body from the HTTP response
        headers, body = http_response.split('\r\n\r\n', 1)

        # Convert the JSON body to a Python dictionary
        print(f'BOdy: {body}')
        body_dict = json.loads(body)
        reference = self.parse_http_response_to_schema(body_dict, path)

        entry_dict = {}
        # Build the OpenAPI response example
        if len(body_dict) == 1:
            entry_dict["id"] = {"value": body_dict}
        else:
            for entry in body_dict:
                key = entry.get("title") or entry.get("name") or entry.get("id")
                entry_dict[key] = {"value": entry}

        return entry_dict, reference

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

    def extract_endpoints(self, note):
        # Define a dictionary to hold the endpoint data
        required_endpoints = {}

        # Use regular expression to find all lines with endpoint definitions
        pattern = r"(\d+\.\s+GET)\s(/[\w{}]+)"
        matches = re.findall(pattern, note)

        # Process each match to populate the dictionary
        for match in matches:
            method, endpoint = match
            method = method.split()[1]  # Split to get rid of the numbering and keep "GET"
            if endpoint in required_endpoints:
                if method not in required_endpoints[endpoint]:
                    required_endpoints[endpoint].append(method)
            else:
                required_endpoints[endpoint] = [method]

        return required_endpoints

    def read_yaml_to_string(self, filepath):
        """
        Reads a YAML file and returns its contents as a string.

        :param filepath: Path to the YAML file.
        :return: String containing the file contents.
        """
        try:
            with open(filepath, 'r') as file:
                file_contents = file.read()
            return file_contents
        except FileNotFoundError:
            print(f"Error: The file {filepath} does not exist.")
            return None
        except IOError as e:
            print(f"Error reading file {filepath}: {e}")
            return None

    def check_openapi_spec(self, note):
        """
            Uses OpenAI's GPT model to generate a complete OpenAPI specification based on a natural language description.

            Parameters:
            - api_key: str. Your OpenAI API key.
            - file_path: str. Path to the YAML file to update.
            - description: str. A detailed description of the entire API.
            """
        description = self.extract_description(note)
        from hackingBuddyGPT.usecases.web_api_testing.yaml_assistant import YamlFileAssistant
        yaml_file_assistant = YamlFileAssistant(self.file_path, self.llm_handler.llm)
        yaml_file_assistant.run(description)

    def extract_description(self, note):
        return note.action.content

    def parse_http_response_to_schema(self, body_dict, path):
        # Create object name
        object_name = path.split("/")[1].capitalize()
        object_name = object_name[:len(object_name) - 1]

        # Parse body dict to types
        properties_dict = {}
        if len(body_dict) == 1:
            properties_dict["id"] = {"type": "int", "format": "uuid", "example": str(body_dict["id"])}
        else:
            for param in body_dict:
                for key, value in param.items():
                    if key == "id":
                        properties_dict[key] = {"type": str(type(value).__name__), "format": "uuid", "example": str(value)}
                    else:
                        properties_dict[key] = {"type": str(type(value).__name__), "example": str(value)}
                break

        object_dict = {"type": "object", "properties": properties_dict}

        if not object_name in self.openapi_spec["components"]["schemas"].keys():
            self.openapi_spec["components"]["schemas"][object_name] = object_dict

        schemas = self.openapi_spec["components"]["schemas"]
        self.schemas = schemas
        print(f'schemas: {schemas}')
        reference = "#/components/schemas/" + object_name
        return reference
