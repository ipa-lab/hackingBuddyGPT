import json
import os.path

import yaml


class OpenAPISpecificationConverter:
    """
    OpenAPISpecificationConverter is a class for converting OpenAPI specification files between YAML and JSON formats.

    Attributes:
        base_directory (str): The base directory for the output files.
    """

    def __init__(self, base_directory):
        """
        Initializes the OpenAPISpecificationConverter with the specified base directory.

        Args:
            base_directory (str): The base directory for the output files.
        """
        self.base_directory = base_directory

    def convert_file(self, input_filepath, output_directory, input_type, output_type):
        """
        Converts files between YAML and JSON formats.

        Args:
            input_filepath (str): The path to the input file.
            output_directory (str): The subdirectory for the output files.
            input_type (str): The type of the input file ('yaml' or 'json').
            output_type (str): The type of the output file ('json' or 'yaml').

        Returns:
            str: The path to the converted output file, or None if an error occurred.
        """
        try:
            filename = os.path.basename(input_filepath)
            output_filename = filename.replace(f".{input_type}", f".{output_type}")
            output_path = os.path.join(self.base_directory, output_directory, output_filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(input_filepath, "r") as infile:
                if input_type == "yaml":
                    content = yaml.safe_load(infile)
                else:
                    content = json.load(infile)

            with open(output_path, "w") as outfile:
                if output_type == "yaml":
                    yaml.dump(content, outfile, allow_unicode=True, default_flow_style=False)
                else:
                    json.dump(content, outfile, indent=2)

            print(f"Successfully converted {input_filepath} to {output_filename}")
            return output_path

        except Exception as e:
            print(f"Error converting {input_filepath}: {e}")
            return None

    def yaml_to_json(self, yaml_filepath):
        """
        Converts a YAML file to a JSON file.

        Args:
            yaml_filepath (str): The path to the YAML file to be converted.

        Returns:
            str: The path to the converted JSON file, or None if an error occurred.
        """
        return self.convert_file(yaml_filepath, "json", "yaml", "json")

    def json_to_yaml(self, json_filepath):
        """
        Converts a JSON file to a YAML file.

        Args:
            json_filepath (str): The path to the JSON file to be converted.

        Returns:
            str: The path to the converted YAML file, or None if an error occurred.
        """
        return self.convert_file(json_filepath, "yaml", "json", "yaml")

    def extract_openapi_info(self, openapi_spec_file, output_path=""):
        """
        Extracts relevant information from an OpenAPI specification and writes it to a JSON file.

        Args:
            openapi_spec (dict): The OpenAPI specification loaded as a dictionary.
            output_file_path (str): Path to save the extracted information in JSON format.

        Returns:
            dict: The extracted information saved in JSON format.
        """
        openapi_spec = json.load(open(openapi_spec_file))

        # Extract the API description and host URL
        description = openapi_spec.get("info", {}).get("description", "No description provided.")
        host = openapi_spec.get("servers", [{}])[0].get("url", "No host URL provided.")

        # Extract correct endpoints and query parameters
        correct_endpoints = []
        query_params = {}

        for path, path_item in openapi_spec.get("paths", {}).items():
            correct_endpoints.append(path)
            # Collect query parameters for each endpoint
            endpoint_query_params = []
            for method, operation in path_item.items():
                if isinstance(operation, dict):
                    if "parameters" in operation.keys():
                        parameters = operation.get("parameters", [])
                        for param in parameters:
                            if param.get("in") == "query":
                                endpoint_query_params.append(param.get("name"))

            if endpoint_query_params:
                query_params[path] = endpoint_query_params

        # Create the final output structure
        extracted_info = {
            "token": "your_api_token_here",
            "host": host,
            "description": description,
            "correct_endpoints": correct_endpoints,
            "query_params": query_params
        }
        filename = os.path.basename(openapi_spec_file)
        filename = filename.replace("_oas", "_config")
        base_name, _ = os.path.splitext(filename)
        output_filename = f"{base_name}.json"
        output_path = os.path.join(output_path, output_filename)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write to JSON file
        with open(output_path, 'w') as json_file:
            json.dump(extracted_info, json_file, indent=2)
        print(f'output path:{output_path}')

        return extracted_info


# Usage example
if __name__ == "__main__":
    # yaml_input = "src/hackingBuddyGPT/usecases/web_api_testing/configs/test_config.json/hard/coincap_oas.json"

    converter = OpenAPISpecificationConverter("converted_files")
    ## Convert YAML to JSON
    # json_file = converter.yaml_to_json(yaml_input)
    #
    ## Convert JSON to YAML
    # if json_file:
    #    converter.json_to_yaml(json_file)

    openapi_path = "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/tests/test_files/oas/fakeapi_oas.json"
    converter.extract_openapi_info(openapi_path,
                                   output_path="/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/tests/test_files")
