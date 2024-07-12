import yaml

class OpenAPISpecificationParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.api_data = self.load_yaml()

    def load_yaml(self):
        """Load YAML data from the specified file."""
        with open(self.filepath, 'r') as file:
            return yaml.safe_load(file)

    def get_servers(self):
        """Retrieve the list of server URLs."""
        return [server['url'] for server in self.api_data.get('servers', [])]

    def get_paths(self):
        """Retrieve all API paths and their methods."""
        paths_info = {}
        paths = self.api_data.get('paths', {})
        for path, methods in paths.items():
            paths_info[path] = {method: details for method, details in methods.items()}
        return paths_info

    def get_operations(self, path):
        """Retrieve operations for a specific path."""
        return self.api_data['paths'].get(path, {})

    def print_api_details(self):
        """Prints details of the API extracted from the OpenAPI document."""
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
        '/hackingBuddyGPT/usecases/web_api_testing/openapi_spec/openapi_spec_2024-06-13_17-16-25.yaml')
    openapi_parser.print_api_details()
