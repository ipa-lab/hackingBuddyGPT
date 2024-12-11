import json
import os
from pathlib import Path
from typing import Dict, List, Union

import yaml


class OpenAPISpecificationParser:
    """
    OpenAPISpecificationParser is a class for parsing and extracting information from an OpenAPI specification file.

    Attributes:
        filepath (str): The path to the OpenAPI specification YAML file.
        api_data (Dict[str, Union[Dict, List]]): The parsed data from the YAML file.
    """

    def __init__(self, filepath: str):
        """
        Initializes the OpenAPISpecificationParser with the specified file path.

        Args:
            filepath (str): The path to the OpenAPI specification YAML file.
        """
        self.filepath: str = filepath
        self.api_data: Dict[str, Union[Dict, List]] = self.load_file(filepath=self.find_oas(filepath=filepath))
        self.oas_path = self.find_oas(filepath)

    def load_file(self, filepath="") -> Dict[str, Union[Dict, List]]:
        """
        Loads YAML data from the specified file.

        Returns:
            Dict[str, Union[Dict, List]]: The parsed data from the YAML file.
        """
        if filepath.endswith(".yaml"):
            with open(self.filepath, "r") as file:
                return yaml.safe_load(file)
        else:
            with open(filepath, 'r', encoding='utf-8') as file:
                return json.load(file)

    def _get_servers(self) -> List[str]:
        """
        Retrieves the list of server URLs from the OpenAPI specification.

        Returns:
            List[str]: A list of server URLs.
        """
        return [server["url"] for server in self.api_data.get("servers", [])]

    def get_endpoints(self) -> Dict[str, Dict[str, Dict]]:
        """
        Retrieves all API paths and their methods from the OpenAPI specification.

        Returns:
            Dict[str, Dict[str, Dict]]: A dictionary with API paths as keys and methods as values.
        """
        paths_info: Dict[str, Dict[str, Dict]] = {}
        paths: Dict[str, Dict[str, Dict]] = self.api_data.get("paths", {})
        for path, methods in paths.items():
            paths_info[path] = {method: details for method, details in methods.items()}
        return paths_info

    def _get_operations(self, path: str) -> Dict[str, Dict]:
        """
        Retrieves operations for a specific path from the OpenAPI specification.

        Args:
            path (str): The API path to retrieve operations for.

        Returns:
            Dict[str, Dict]: A dictionary with methods as keys and operation details as values.
        """
        return self.api_data["paths"].get(path, {})

    def _print_api_details(self) -> None:
        """
        Prints details of the API extracted from the OpenAPI document, including title, version, servers,
        paths, and operations.
        """
        print("API Title:", self.api_data["info"]["title"])
        print("API Version:", self.api_data["info"]["version"])
        print("Servers:", self._get_servers())
        print("\nAvailable Paths and Operations:")
        for path, operations in self.get_paths().items():
            print(f"\nPath: {path}")
            for operation, details in operations.items():
                print(f"  Operation: {operation.upper()}")
                print(f"    Summary: {details.get('summary')}")
                print(f"    Description: {details['responses']['200']['description']}")

    def find_oas(self, filepath):
        current_file_path = os.path.dirname(filepath)
        file_name = Path(filepath).name.split("_config")[0]
        oas_file_path = os.path.join(current_file_path, "oas", file_name + "_oas.json")
        print(f'OpenAPI specification file: {oas_file_path}')
        return oas_file_path

    def get_schemas(self) -> Dict[str, Dict]:
        """Retrieve schemas from OpenAPI JSON data."""
        components = self.api_data.get('components', {})
        schemas = components.get('schemas', {})
        return schemas

    def get_protected_endpoints(self):
        protected = []
        for path, operations in self.api_data['paths'].items():
            for operation, details in operations.items():
                if 'security' in details:
                    protected.append(f"{operation.upper()} {path}")
        return protected

    def get_refresh_endpoints(self):
        refresh_endpoints = []
        for path, operations in self.api_data['paths'].items():
            if 'refresh' in path.lower():
                refresh_endpoints.extend([f"{op.upper()} {path}" for op in operations])
        return refresh_endpoints

    def classify_endpoints(self):
        classifications = {
            'resource_intensive_endpoint': [],
            'public_endpoint': [],
            'secure_action_endpoint': [],
            'role_access_endpoint': [],
            'sensitive_data_endpoint': [],
            'sensitive_action_endpoint': [],
            'protected_endpoint': [],
            'refresh_endpoint': [],
            'login_endpoint': [],
            'authentication_endpoint': [],
            'unclassified_endpoint': [],
            'account_creation':[]
        }

        for path, path_item in self.api_data['paths'].items():
            for method, operation in path_item.items():
                classified = False
                description = operation.get('description', '').lower()
                security = operation.get('security', '').lower()
                responses = operation.get("responses", {})
                unauthorized_description = responses.get("401", {}).get("description", "").lower()
                forbidden_description = responses.get("403", {}).get("description", "").lower()
                too_many_requests_description = responses.get("429", {}).get("description", "").lower()

                # Public endpoint: No '401 Unauthorized' response or description doesn't mention 'unauthorized'
                if ('Unauthorized' not in unauthorized_description
                        or "forbidden" in forbidden_description
                        or "too many requests" in too_many_requests_description
                        and not security):
                    classifications['public_endpoint'].append((method.upper(), path))
                    classified = True

                # Protected endpoints: Paths mentioning "user" or "admin" explicitly
                if (any(keyword in path.lower() for keyword in ["user", "admin"])
                        and not any(keyword in path.lower() for keyword in ["api"])) \
                    and security:
                    classifications['protected_endpoint'].append((method.upper(), path))
                    classified = True

                # Secure action endpoints: Identified by roles or protected access
                if any(keyword in path.lower() for keyword in ["user", "admin"]):
                    classifications['role_access_endpoint'].append((method.upper(), path))
                    classified = True

                # Sensitive data or action endpoints: Based on description
                if any(word in description for word in ['sensitive', 'confidential']):
                    classifications['sensitive_data_endpoint'].append((method.upper(), path))
                    classified = True

                if any(word in description for word in ['delete', 'modify', 'change']):
                    classifications['sensitive_action_endpoint'].append((method.upper(), path))
                    classified = True

                # Resource-intensive endpoints
                if any(word in description for word in ['upload', 'batch', 'heavy', 'intensive']):
                    classifications['resource_intensive_endpoint'].append((method.upper(), path))
                    classified = True

                # Refresh endpoints
                if 'refresh' in path.lower() or 'refresh' in description:
                    classifications['refresh_endpoint'].append((method.upper(), path))
                    classified = True
                # User creation endpoint
                if any(keyword in path.lower() for keyword in ['user', 'users']) and not "login" in path:
                    if method.upper() == "POST":
                        classifications["account_creation"].append((method.upper(), path))
                    classified = True
                # Login endpoints
                if any(keyword in path.lower() for keyword in ['login', 'signin', 'sign-in']):
                    if method.upper() == "POST":
                        classifications['login_endpoint'].append((method.upper(), path))
                        classified = True

                # Authentication-related endpoints
                if any(keyword in path.lower() or keyword in description for keyword in
                       ['auth', 'authenticate', 'token', 'register']):
                    classifications['authentication_endpoint'].append((method.upper(), path))
                    classified = True

                # Unclassified endpoints
                if not classified:
                    classifications['unclassified_endpoint'].append((method.upper(), path))

        return classifications


if __name__ == "__main__":  # Usage
    parser = OpenAPISpecificationParser(
        "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/configs/hard/reqres_config.json")

    endpoint_classes = parser.classify_endpoints()
    for category, endpoints in endpoint_classes.items():
        print(f"{category}: {endpoints}")
