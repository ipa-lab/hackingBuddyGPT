from dataclasses import dataclass

import yaml

from . import Capability


@dataclass
class YAMLFile(Capability):
    def describe(self) -> str:
        return "Takes a Yaml file and updates it with the given information"

    def __call__(self, yaml_str: str) -> str:
        """
        Updates a YAML string based on provided inputs and returns the updated YAML string.

        Args:
        yaml_str (str): Original YAML content in string form.
        updates (dict): A dictionary representing the updates to be applied.

        Returns:
        str: Updated YAML content as a string.
        """
        try:
            # Load the YAML content from string
            data = yaml.safe_load(yaml_str)

            print(f"Updates:{yaml_str}")

            # Apply updates from the updates dictionary
            # for key, value in updates.items():
            #    if key in data:
            #        data[key] = value
            #    else:
            #        print(f"Warning: Key '{key}' not found in the original data. Adding new key.")
            #        data[key] = value
            #
            ## Convert the updated dictionary back into a YAML string
            # updated_yaml_str = yaml.safe_dump(data, sort_keys=False)
            # return updated_yaml_str
        except yaml.YAMLError as e:
            print(f"Error processing YAML data: {e}")
            return "None"
