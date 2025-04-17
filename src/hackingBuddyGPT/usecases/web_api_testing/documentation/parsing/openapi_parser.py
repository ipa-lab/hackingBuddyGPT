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
        valid_methods = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
        path_item = self.api_data.get("paths", {}).get(path, {})
        return {method: details for method, details in path_item.items() if method.lower() in valid_methods}

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

    def find_oas(self, filepath) -> str:
        """

        Gets the OpenAPI specification for the config
        Args:
            filepath (str): The config path

        Returns:
            str: The OAS file path
        """
        current_file_path = os.path.dirname(filepath)

        file_name = Path(filepath).name.split("_config")[0]
        oas_file_path = os.path.join(current_file_path, "oas", file_name + "_oas.json")
        return oas_file_path

    def get_schemas(self) -> Dict[str, Dict]:
        """
                Retrieve schemas from OpenAPI JSON data.


                Returns:
                    Dict[str, Dict]: A dictionary with schemas
        """

        components = self.api_data.get('components', {})
        schemas = components.get('schemas', {})
        return schemas

    def get_protected_endpoints(self) -> List:
        """
               Retrieves protected endpoints from api data.


               Returns:
                   List: A list of protected endpoints
        """
        protected = []
        for path, operations in self.api_data['paths'].items():
            for operation, details in operations.items():
                if 'security' in details:
                    protected.append(f"{operation.upper()} {path}")
        return protected

    def get_refresh_endpoints(self):
        """
                Retrieves refresh endpoints from api data.


                Returns:
                    List: A list of refresh endpoints
         """
        refresh_endpoints = []
        for path, operations in self.api_data['paths'].items():
            if 'refresh' in path.lower():
                refresh_endpoints.extend([f"{op.upper()} {path}" for op in operations])
        return refresh_endpoints

    def get_schema_for_endpoint(self, path, method):
        """
        Retrieve the schema for a specific endpoint method.

        Args:
            path (str): The endpoint path.
            method (str): The HTTP method (e.g., 'get', 'post').

        Returns:
            dict: The schema for the requestBody, or None if not available.
        """
        method_details = self.api_data.get("paths", {}).get(path, {}).get(method.lower(), {})
        request_body = method_details.get("requestBody", {})

        # Safely get the schema
        content = request_body.get("content", {})
        application_json = content.get("application/json", {})
        schema = application_json.get("schema", None)
        schema_ref = None

        if schema and isinstance(schema, dict):
            schema_ref = schema.get("$ref", None)

        schemas = self.get_schemas()
        correct_schema = None
        if schema_ref is not None:
            ref_list = schema_ref.split("/")
            for schema in schemas:
                if schema in ref_list:
                    correct_schema = schemas.get(schema)
                    return correct_schema

        return None

    def classify_endpoints(self, name=""):
        """
        Classifies API endpoints into various security and functionality categories based on heuristics
        such as URL patterns, HTTP methods, response codes, descriptions, and security settings.

        This method processes all endpoints defined in `self.api_data['paths']` and assigns them
        into predefined classes including public, protected, resource-intensive, login, and others.
        Classifications are based on path structure, method, presence of authentication/authorization,
        keywords in the path or description, and response status codes.

        Args:
            name (str, optional): An optional string (e.g., test name or profile name) that can
                influence the classification of certain endpoints (e.g., skipping account creation
                classification for specific OWASP test cases). Defaults to "".

        Returns:
            dict: A dictionary containing classified endpoints under the following keys:
                - 'resource_intensive_endpoint': Endpoints involving batch uploads or processing.
                - 'public_endpoint': Endpoints accessible without authentication.
                - 'secure_action_endpoint': Endpoints performing sensitive operations.
                - 'role_access_endpoint': Endpoints involving user/admin roles.
                - 'sensitive_data_endpoint': Endpoints returning sensitive/confidential data.
                - 'sensitive_action_endpoint': Endpoints performing critical modifications.
                - 'protected_endpoint': Endpoints requiring authentication.
                - 'refresh_endpoint': Endpoints related to token/session refreshing.
                - 'login_endpoint': Endpoints used for user login or sign-in.
                - 'authentication_endpoint': Endpoints dealing with authentication or token handling.
                - 'account_creation': Endpoints related to user account creation.
                - 'unclassified_endpoint': Endpoints that do not match any specific classification.
        """
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
            'account_creation': []
        }

        for path, path_item in self.api_data['paths'].items():
            for method, operation in path_item.items():
                schema = self.get_schema_for_endpoint(path, method)
                if method == 'get' and schema == None and "parameters" in operation.keys() and len(
                        operation.get("parameters", [])) > 0:
                    schema = operation.get("parameters")[0]
                classified = False
                parameters = operation.get("parameters", [])
                description = operation.get('description', '').lower()
                security = operation.get('security', {})
                responses = operation.get("responses", {})
                unauthorized_description = responses.get("401", {}).get("description", "").lower()
                forbidden_description = responses.get("403", {}).get("description", "").lower()
                too_many_requests_description = responses.get("429", {}).get("description", "").lower()

                if "dashboard" in path:
                    classifications['unclassified_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True
                    continue

                # Protected endpoints: Paths mentioning "user" or "admin" explicitly
                # Check if the path mentions "user" or "admin" and doesn't include "api"
                path_condition = (
                        any(keyword in path for keyword in ["user", "admin"])
                        and not any(keyword in path for keyword in ["api"])
                )

                # Check if any parameter's value equals "Authorization-Token"
                parameter_condition = any(
                    param.get("name") == "Authorization-Token" for param in parameters
                )

                auth_condition = 'Unauthorized' in unauthorized_description or "forbidden" in forbidden_description

                # Combined condition with `security` (adjust based on actual schema requirements)
                if (path_condition or parameter_condition or auth_condition) or security:
                    classifications['protected_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Public endpoint: No '401 Unauthorized' response or description doesn't mention 'unauthorized'
                if ('Unauthorized' not in unauthorized_description
                        or "forbidden" not in forbidden_description
                        or "too many requests" not in too_many_requests_description
                        and not security):
                    classifications['public_endpoint'].append(
                        {
                            "method": method.upper(),
                            "path": path,
                            "schema": schema}
                    )
                    classified = True

                    # User creation endpoint
                    if any(keyword in path.lower() for keyword in
                           ['user', 'users', 'signup']) and not "login" in path or any(
                        word in description for word in ['create a user']):

                        if path.lower().endswith("user") and name.startswith("OWASP"):
                            continue
                        if not any(keyword in path.lower() for keyword in
                                   ['pictures', 'verify-email-token', 'change-email', "reset", "verify", "videos",
                                    "mechanic"]):
                            if method.upper() == "POST" and not "data-export" in path:
                                classifications["account_creation"].append({
                                    "method": method.upper(),
                                    "path": path,
                                    "schema": schema})
                                classified = True

                # Secure action endpoints: Identified by roles or protected access
                if any(keyword in path.lower() for keyword in ["user", "admin"]):
                    classifications['role_access_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Sensitive data or action endpoints: Based on description
                if any(word in description for word in ['sensitive', 'confidential']):
                    classifications['sensitive_data_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                if any(word in description for word in ['delete', 'modify', 'change']):
                    classifications['sensitive_action_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Resource-intensive endpoints
                if any(word in description for word in ['upload', 'batch', 'heavy', 'intensive']):
                    classifications['resource_intensive_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Rate-limited endpoints
                if '429' in responses and 'too many requests' in responses['429'].get('description', '').lower():
                    classifications['resource_intensive_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Refresh endpoints
                if 'refresh' in path.lower() or 'refresh' in description:
                    classifications['refresh_endpoint'].append({
                        "method": method.upper(),
                        "path": path,
                        "schema": schema})
                    classified = True

                # Login endpoints
                if any(keyword in path.lower() for keyword in ['login', 'signin', 'sign-in']):
                    if method.upper() == "POST":
                        classifications['login_endpoint'].append({
                            "method": method.upper(),
                            "path": path,
                            "schema": schema})
                        classified = True

                # Authentication-related endpoints
                if any(keyword in path.lower() or keyword in description for keyword in
                       ['auth', 'authenticate', 'token', 'register']):
                    classifications['authentication_endpoint'].append(
                        {
                            "method": method.upper(),
                            "path": path,
                            "schema": schema}
                    )
                    classified = True

                # Unclassified endpoints
                if not classified:
                    if isinstance(method, dict):
                        for method, path in classifications.items():  # Iterate over dictionary items
                            # Now we can use .upper() on the 'method' string
                            classifications['unclassified_endpoint'].append({
                                "method": method.upper(),
                                "path": path,
                                "schema": schema})
                    else:
                        classifications['unclassified_endpoint'].append(
                            {
                                "method": method.upper(),
                                "path": path,
                                "schema": schema})

        return classifications

    def categorize_endpoints(self, endpoints, query: dict):
        """
          Categorizes a list of API endpoints based on their path structure.

          This method inspects the number of path segments in each endpoint to determine
          its type (e.g., root-level, instance-level, subresource, etc.). It uses basic
          heuristics, such as the presence of the keyword "id" and the number of segments
          after splitting the path by slashes.

          Args:
              endpoints (list): A list of API endpoint strings (e.g., ['/users', '/users/{id}']).
              query (dict): A dictionary of query parameters (typically used in GET requests).
                            The values of this dictionary are included in the result under the 'query' key.

          Returns:
              dict: A dictionary categorizing the endpoints into the following types:
                  - 'root_level': Endpoints with a single path segment (e.g., '/users').
                  - 'instance_level': Endpoints that include one path parameter like 'id' (e.g., '/users/{id}').
                  - 'subresource': Endpoints with two segments that don't include 'id' (e.g., '/users/profile').
                  - 'related_resource': Endpoints with three segments including 'id' (e.g., '/users/{id}/orders').
                  - 'multi-level_resource': Endpoints with more than two segments not matched by the above.
                  - 'query': The values from the input query dictionary."""
        root_level = []
        single_parameter = []
        subresource = []
        related_resource = []
        multi_level_resource = []

        for endpoint in endpoints:
            # Split the endpoint by '/' and filter out empty strings
            parts = [part for part in endpoint.split('/') if part]

            # Determine the category based on the structure
            if len(parts) == 1:
                root_level.append(endpoint)
            elif len(parts) == 2:
                if "id" in endpoint:
                    single_parameter.append(endpoint)
                else:
                    subresource.append(endpoint)
            elif len(parts) == 3:
                if "id" in endpoint:
                    related_resource.append(endpoint)
                else:
                    multi_level_resource.append(endpoint)
            else:
                multi_level_resource.append(endpoint)

        return {
            "root_level": root_level,
            "instance_level": single_parameter,
            "subresource": subresource,
            "query": query.values(),
            "related_resource": related_resource,
            "multi-level_resource": multi_level_resource,
        }


if __name__ == "__main__":  # Usage
    parser = OpenAPISpecificationParser(
        "/config/hard/reqres_config.json")

    endpoint_classes = parser.classify_endpoints()
    for category, endpoints in endpoint_classes.items():
        print(f"{category}: {endpoints}")
