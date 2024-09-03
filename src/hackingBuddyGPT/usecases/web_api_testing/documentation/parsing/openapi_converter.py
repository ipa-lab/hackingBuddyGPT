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


# Usage example
if __name__ == "__main__":
    yaml_input = "/home/diana/Desktop/masterthesis/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/openapi_spec/openapi_spec_2024-06-13_17-16-25.yaml"

    converter = OpenAPISpecificationConverter("converted_files")
    # Convert YAML to JSON
    json_file = converter.yaml_to_json(yaml_input)

    # Convert JSON to YAML
    if json_file:
        converter.json_to_yaml(json_file)
