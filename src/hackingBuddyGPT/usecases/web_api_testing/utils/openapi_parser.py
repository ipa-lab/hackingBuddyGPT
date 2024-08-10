import yaml

class OpenAPISpecificationParser:
    """
    OpenAPISpecificationParser is a class for parsing and extracting information from an OpenAPI specification file.

    Attributes:
        filepath (str): The path to the OpenAPI specification YAML file.
        api_data (dict): The parsed data from the YAML file.
    """

    def __init__(self, filepath):
        """
        Initializes the OpenAPISpecificationParser with the specified file path.

        Args:
            filepath (str): The path to the OpenAPI specification YAML file.
        """
        self.filepath = filepath
        self.api_data = self.load_yaml()

    def load_yaml(self):
        """
        Loads YAML data from the specified file.

        Returns:
            dict: The parsed data from the YAML file.
        """
        with open(self.filepath, 'r') as file:
            return yaml.safe_load(file)

    def get_servers(self):
        """
        Retrieves the list of server URLs from the OpenAPI specification.

        Returns:
            list: A list of server URLs.
        """
        return [server['url'] for server in self.api_data.get('servers', [])]

    def get_paths(self):
        """
        Retrieves all API paths and their methods from the OpenAPI specification.

        Returns:
            dict: A dictionary with API paths as keys and methods as values.
        """
        paths_info = {}
        paths = self.api_data.get('paths', {})
        for path, methods in paths.items():
            paths_info[path] = {method: details for method, details in methods.items()}
        return paths_info

    def get_operations(self, path):
        """
        Retrieves operations for a specific path from the OpenAPI specification.

        Args:
            path (str): The API path to retrieve operations for.

        Returns:
            dict: A dictionary with methods as keys and operation details as values.
        """
        return self.api_data['paths'].get(path, {})

    def print_api_details(self):
        """
        Prints details of the API extracted from the OpenAPI document, including title, version, servers,
        paths, and operations.
        """
        print("API Title:", self.api_data['info']['title'])
        print("API Version:", self.api_data['info']['version'])
        print("Servers:", self.get_servers())
        print("\nAvailable Paths and Operations:")
        for path, operations in self.get_paths().items():
            print(f"\nPath: {path}")
            for operation, details in operations.items():
                print(f"  Operation: {operation.upper()}")
                print(f"    Summary: {details.get('summary')}")
                print(f"    Description: {details['responses']['200']['description']}")

# Usage example
if __name__ == '__main__':
    openapi_parser = OpenAPISpecificationParser(
        '/hackingBuddyGPT/usecases/web_api_testing/openapi_spec/openapi_spec_2024-06-13_17-16-25.yaml'
    )
    openapi_parser.print_api_details()
