import os.path

import yaml
import json
class OpenAPISpecificationConverter:
    def __init__(self, filepath):
        self.filepath = filepath
    def yaml_to_json(self, yaml_filepath):
        """
        Convert a YAML file to a JSON file.

        :param yaml_filepath: Path to the input YAML file.
        """
        try:
            # Get the filename from the path
            filename = os.path.basename(yaml_input)
            json_filepath = filename.split(".yaml")[0]+ ".json"
            converted_path = os.path.join(self.filepath, "json")
            if not os.path.exists(converted_path) :
                os.makedirs(converted_path, exist_ok=True)
            with open(yaml_filepath, 'r') as yaml_file:
                yaml_content = yaml.safe_load(yaml_file)
            final_path = os.path.join(converted_path, json_filepath)
            with open(final_path, 'w') as json_file:
                json.dump(yaml_content, json_file, indent=2)

            print(f"Successfully converted {yaml_filepath} to {json_filepath}")
            return final_path
        except Exception as e:
            print(f"Error converting YAML to JSON: {e}")
            return ""


    def json_to_yaml(self,json_filepath):
        """
        Convert a JSON file to a YAML file.

        :param json_filepath: Path to the input JSON file.
        """
        try:
            # Get the filename from the path
            filename = os.path.basename(json_filepath)
            yaml_filepath = filename.split(".json")[0] + ".yaml"
            converted_path = os.path.join(self.filepath, "yaml")
            if not os.path.exists(converted_path):
                os.makedirs(converted_path, exist_ok=True)
            with open(json_filepath, 'r') as json_file:
                json_content = json.load(json_file)
            final_path = os.path.join(converted_path, yaml_filepath)

            with open(final_path, 'w') as yaml_file:
                yaml.dump(json_content, yaml_file, allow_unicode=True, default_flow_style=False)

            print(f"Successfully converted {json_filepath} to {yaml_filepath}")
        except Exception as e:
            print(f"Error converting JSON to YAML: {e}")


# Usage example
if __name__ == '__main__':
    yaml_input = '/home/diana/Desktop/masterthesis/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/openapi_spec/openapi_spec_2024-06-13_17-16-25.yaml'

    converter = OpenAPISpecificationConverter("converted_files")
    # Convert YAML to JSON
    json_file = converter.yaml_to_json(yaml_input)

    # Convert JSON to YAML
    yaml_file = converter.json_to_yaml(json_file)