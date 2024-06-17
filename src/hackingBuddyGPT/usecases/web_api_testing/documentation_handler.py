import os
import re

import openai
import pydantic_core
import yaml
from datetime import datetime

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model
from hackingBuddyGPT.capabilities.yamlFile import YAMLFile


class DocumentationHandler:
    """Handles the generation and updating of an OpenAPI specification document based on dynamic API responses."""

    def __init__(self, llm, capabilities):
        """Initializes the handler with a template OpenAPI specification."""
        self.filename = f"openapi_spec_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.yaml"
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Generated API Documentation",
                "version": "1.0",
                "description": "Automatically generated description of the API."
            },
            "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
            "endpoints": {}
        }
        self.llm = llm
        self.api_key = llm.api_key
        self.capabilities = capabilities
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "openapi_spec")
        self.file = os.path.join(self.file_path, self.filename)
        yamls = []
        self._capabilities = {
            "yaml": YAMLFile()
        }


    def update_openapi_spec(self, resp):
        """
        Updates the OpenAPI specification based on the API response provided.

        Args:
        - response: The response object containing details like the path and method which should be documented.
        """
        request = resp.action
        print(f'Type of request:{type(request)}')
        print(f'is recordnote? {isinstance(request, RecordNote)}')
        print(f'is HTTP request? {isinstance(request, HTTPRequest)}')
        print(f'is HTTP request? {type(request)}')
        print(f'is HTTP request? {type(request) == HTTPRequest}')
        print("same class?")
        print(request.__class__.__name__ == 'HTTPRequest')

        if request.__class__.__name__ == 'RecordNote': # TODO check why isinstance does not work
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
                self.openapi_spec['endpoints'][path][method.lower()] = {
                    "summary": f"{method} operation on {path}",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}  # Simplified for example
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
                "paths": self.openapi_spec["endpoints"]
            }


            # Create directory if it doesn't exist and generate the timestamped filename
            os.makedirs(self.file_path, exist_ok=True)

            # Write to YAML file
            with open(self.file , 'w') as yaml_file:
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

        # Prepare the prompt for the LLM to generate the entire OpenAPI YAML
        prompt =[{'role': 'system', 'content': f"Update the OpenAPI specification in YAML format based on the following description of an API and return only the OpenAPI specification as a yaml:" \
                f"\n Description:{description},\n yaml:{self.read_yaml_to_string(self.file)}"}]


        # Ask the model to generate the complete YAML specification
        openai.api_key = self.api_key
        # Making the API call to GPT-3.5
        try:
            response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model,
                                                                                               messages=prompt,
                                                                                               response_model=capabilities_to_action_model(
                                                                                                   self._capabilities))

            message = completion.choices[0].message
            tool_call_id = message.tool_calls[0].id
            command = pydantic_core.to_json(response).decode()
            print(f'command:{command}')
            result = response.execute()
            print(f'result:\n{result}')
        except Exception as e:
            print(f"An error occurred: {e}")
            raise Exception(e)
        #response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model, messages=prompt, response_model=capabilities_to_action_model(self.capabilities))

       ## Parse the model's response assuming it's a valid YAML
       #print(f'new yaml file:{completion.choices[0].message}')
       #new_openapi_spec = yaml.safe_load(completion.choices[0].message)
       #
       ## Write the generated YAML back to file
       #with open(self.file, 'w') as file:
       #    yaml.safe_dump(new_openapi_spec, file, default_flow_style=False, sort_keys=False)

    def extract_description(self, note):
        return note.action.content

