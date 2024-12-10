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
        self.api_data: Dict[str, Union[Dict, List]] = self.load_yaml()

    def load_yaml(self) -> Dict[str, Union[Dict, List]]:
        """
        Loads YAML data from the specified file.

        Returns:
            Dict[str, Union[Dict, List]]: The parsed data from the YAML file.
        """
        with open(self.filepath, "r") as file:
            return yaml.safe_load(file)

    def _get_servers(self) -> List[str]:
        """
        Retrieves the list of server URLs from the OpenAPI specification.

        Returns:
            List[str]: A list of server URLs.
        """
        return [server["url"] for server in self.api_data.get("servers", [])]

    def get_paths(self) -> Dict[str, Dict[str, Dict]]:
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
