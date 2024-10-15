import json
from typing import Dict, Optional, Any, List

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.state_learning.state_planning_prompt import (
    StatePlanningPrompt,
)


class InContextLearningPrompt(StatePlanningPrompt):
    """
    A class that generates prompts using the in-context learning strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    in-context learning strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        prompt (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
        turn (int): The round number for which the prompt is being generated.
        purpose (Optional[PromptPurpose]): The purpose of the prompt generation, which can be set during the process.
        open_api_spec (Any) : Samples including the context.
    """
    def __init__(self, context: PromptContext, prompt_helper, context_information: Dict[int, Dict[str, str]], open_api_spec: Any) -> None:
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            context_information (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.IN_CONTEXT)
        self.prompt: Dict[int, Dict[str, str]] = context_information
        self.purpose: Optional[PromptPurpose] = None
        self.open_api_spec = open_api_spec

    def generate_prompt(
        self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Generates a prompt using the in-context learning strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (List[Dict[str, str]]): A list of previous prompt entries, each containing a "content" key.

        Returns:
            str: The generated prompt.
        """
        if self.context == PromptContext.DOCUMENTATION:
            steps =  self._get_documentation_steps("explore", previous_prompt)

        return self.prompt_helper.check_prompt(previous_prompt=previous_prompt, steps=steps)

    def _get_documentation_steps(self, move_type: str, previous_prompt) -> List[str]:
        # Extract properties and example response
        if "endpoints" in self.open_api_spec:
            properties = self.extract_properties()
            example_response = {}
            endpoint = ""
            endpoints = [endpoint for endpoint in self.open_api_spec["endpoints"]]
            if len(endpoints) > 0 :
                previous_prompt = self.sort_previous_prompt(previous_prompt)
                for prompt in previous_prompt:
                    if isinstance(prompt, dict) and prompt["role"] == "system":
                        if endpoints[0] not in prompt["content"]:
                            endpoint = endpoints[0]
                        else:
                            for ep in endpoints:
                                if ep not in prompt["content"]:
                                    endpoint = ep

                                    break

                    #if endpoint != "": break
                method_example_response = self.extract_example_response(self.open_api_spec["endpoints"], endpoint=endpoint)
                icl_prompt = self.generate_icl_prompt(properties, method_example_response, endpoint)
            else:
                icl_prompt = ""
        else:
            icl_prompt = ""
        print(icl_prompt)

        if move_type == "explore":
            return self.prompt_helper._get_initial_documentation_steps(
                [f"Based on this information :\n{icl_prompt}\n Do the following: "],
            strategy=self.strategy)
        else:
            return self.prompt_helper.get_endpoints_needing_help()
    def _get_pentesting_steps(self, move_type: str) -> List[str]:
        pass

    import json

    # Function to extract properties from the schema
    def extract_properties(self):
        properties = self.open_api_spec.get("components", {}).get("schemas", {}).get("Post", {}).get("properties", {})
        extracted_props = {}

        for prop_name, prop_details in properties.items():
            example = prop_details.get("example", "No example provided")
            prop_type = prop_details.get("type", "Unknown type")
            extracted_props[prop_name] = {
                "example": example,
                "type": prop_type
            }

        return extracted_props

    # Function to extract example response from paths
    def extract_example_response(self, api_paths, endpoint, method="get"):
        example_method ={}
        example_response = {}
        # Ensure that the provided endpoint and method exist in the schema
        if endpoint in api_paths and method in api_paths[endpoint]:
            responses = api_paths[endpoint][method].get("responses", {})

            # Check for response code 200 and application/json content type
            if '200' in responses:
                content = responses['200'].get("content", {})
                if "application/json" in content:
                    examples = content["application/json"].get("examples", {})

                    # Extract example responses
                    for example_name, example_details in examples.items():
                        if len(example_response) ==1:
                            break
                        example_value = example_details.get("value", {})
                        example_response[example_name] = example_value

                    example_method[method] = example_response

        return example_method

    # Function to generate the prompt for In-Context Learning
    def generate_icl_prompt(self, properties, example_response, endpoint):
        # Core information about API
        prompt = f"# REST API: {example_response.keys()} {endpoint}\nThis API retrieves objects with the following properties:\n\n"

        # Add properties to the prompt
        for prop, details in properties.items():
            prompt += f"- **{prop}**: {details['type']} (e.g., {details['example']})\n"

        # Add an example response to the prompt
        prompt += "\n**Example Response**:\n```json\n"
        if example_response != {}:
            example_key = list(example_response.keys())[0]  # Take the first example for simplicity
            example_json = json.dumps(example_response[example_key], indent=2)
            prompt += example_json + "\n```\n"

        return prompt

    def sort_previous_prompt(self, previous_prompt):
        sorted_list = []
        for i in range(len(previous_prompt) - 1, -1, -1):
            sorted_list.append(previous_prompt[i])
        return sorted_list

