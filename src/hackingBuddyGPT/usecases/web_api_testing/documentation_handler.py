import os
import yaml
from datetime import datetime


class DocumentationHandler:
    """Handles the generation and updating of an OpenAPI specification document based on dynamic API responses."""

    def __init__(self):
        """Initializes the handler with a template OpenAPI specification."""
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

    def update_openapi_spec(self, response):
        """
        Updates the OpenAPI specification based on the API response provided.

        Args:
        - response: The response object containing details like the path and method which should be documented.
        """
        request = response.action
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

    def write_openapi_to_yaml(self, filename='openapi_spec.yaml'):
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
            file_path = os.path.dirname(filename)
            timestamped_filename = f"{os.path.splitext(filename)[0]}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.yaml"
            os.makedirs(file_path, exist_ok=True)

            # Write to YAML file
            with open(os.path.join(file_path, timestamped_filename), 'w') as yaml_file:
                yaml.dump(openapi_data, yaml_file, allow_unicode=True, default_flow_style=False)
            print(f"OpenAPI specification written to {timestamped_filename}.")
        except Exception as e:
            raise Exception(f"Error writing YAML file: {e}")

