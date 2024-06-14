import os.path

import yaml
import json


class OpenAPISpecificationConverter:
    def __init__(self, base_directory):
        self.base_directory = base_directory

    def convert_file(self, input_filepath, output_directory, input_type, output_type):
        """
        Generic method to convert files between YAML and JSON.

        :param input_filepath: Path to the input file.
        :param output_directory: Subdirectory for the output files.
        :param input_type: Type of the input file ('yaml' or 'json').
        :param output_type: Type of the output file ('json' or 'yaml').
        """
        try:
            filename = os.path.basename(input_filepath)
            output_filename = filename.replace(f".{input_type}", f".{output_type}")
            output_path = os.path.join(self.base_directory, output_directory, output_filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(input_filepath, 'r') as infile:
                if input_type == 'yaml':
                    content = yaml.safe_load(infile)
                else:
                    content = json.load(infile)

            with open(output_path, 'w') as outfile:
                if output_type == 'yaml':
                    yaml.dump(content, outfile, allow_unicode=True, default_flow_style=False)
                else:
                    json.dump(content, outfile, indent=2)

            print(f"Successfully converted {input_filepath} to {output_filename}")
            return output_path

        except Exception as e:
            print(f"Error converting {input_filepath}: {e}")
            return None

    def yaml_to_json(self, yaml_filepath):
        """Convert a YAML file to a JSON file."""
        return self.convert_file(yaml_filepath, "json", 'yaml', 'json')

    def json_to_yaml(self, json_filepath):
        """Convert a JSON file to a YAML file."""
        return self.convert_file(json_filepath, "yaml", 'json', 'yaml')


# Usage example
if __name__ == '__main__':
    yaml_input = '/home/diana/Desktop/masterthesis/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/openapi_spec/openapi_spec_2024-06-13_17-16-25.yaml'

    converter = OpenAPISpecificationConverter("converted_files")
    # Convert YAML to JSON
    json_file = converter.yaml_to_json(yaml_input)

    # Convert JSON to YAML
    yaml_file = converter.json_to_yaml(json_file)