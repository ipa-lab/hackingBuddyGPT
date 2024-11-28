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

    def __init__(self, context: PromptContext, prompt_helper, context_information: Dict[int, Dict[str, str]],
                 open_api_spec: Any) -> None:
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            context_information (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.IN_CONTEXT)
        self.explored_steps = []
        self.prompt: Dict[int, Dict[str, str]] = context_information
        self.purpose: Optional[PromptPurpose] = None
        self.open_api_spec = open_api_spec
        self.response_history = {
        }

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
            steps = self._get_documentation_steps(move_type=move_type, previous_prompt=previous_prompt)
        else:
            steps = self._get_pentesting_steps(move_type=move_type, common_step=previous_prompt)

        return self.prompt_helper.check_prompt(previous_prompt=previous_prompt, steps=steps)

    def _get_documentation_steps(self, move_type: str, previous_prompt) -> List[str]:
        print(f'Move type:{move_type}')
        # Extract properties and example response
        if "endpoints" in self.open_api_spec:
            properties = self.extract_properties()
            example_response = {}
            endpoint = ""
            endpoints = [endpoint for endpoint in self.open_api_spec["endpoints"]]
            if len(endpoints) > 0:
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

                    # if endpoint != "": break
                method_example_response = self.extract_example_response(self.open_api_spec["endpoints"],
                                                                        endpoint=endpoint)
                icl_prompt = self.generate_icl_prompt(properties, method_example_response, endpoint)
            else:
                icl_prompt = ""
        else:
            icl_prompt = ""
        print(icl_prompt)

        if move_type == "explore":
            return self.prompt_helper._get_initial_documentation_steps(
                [f"Based on this information :\n{icl_prompt}\n Do the following: "],
                strategy=self.strategy, strategy_steps=self.get_documentation_steps())
        else:
            return self.prompt_helper.get_endpoints_needing_help(
                info=f"Based on this information :\n{icl_prompt}\n Do the following: ")

    def _get_pentesting_steps(self, move_type: str, common_step: Optional[str] = "") -> List[str]:
        """
        Provides the steps for the chain-of-thought strategy when the context is pentesting.

        Args:
            move_type (str): The type of move to generate.
            common_step (Optional[str]): A common step prefix to apply to each generated step.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the pentesting context.
        """

        explore_steps = self.pentesting_information.explore_steps()
        if move_type == "explore" and hasattr(self,
                                              'pentesting_information') and explore_steps:
            purpose = next(iter(explore_steps))
            steps = explore_steps.get(purpose, [])

            # Transform and generate ICL format
            transformed_steps = self.transform_to_icl_with_previous_examples({purpose: [steps]})
            cot_steps = transformed_steps.get(purpose, [])

            # Process each step while maintaining conditional CoT
            for step in cot_steps:
                if step not in getattr(self, 'explored_steps', []):
                    self.explored_steps.append(step)

                    if purpose not in self.response_history.keys():
                        self.response_history[purpose] = {"step": "", "response": ""}

                    self.response_history.get(purpose).get(step).update({purpose: step})

                    # Apply any common steps
                    if common_step:
                        step = f"{common_step} {step}"

                    # Clean up explore steps once processed
                    if purpose in explore_steps and \
                            explore_steps[purpose]:
                        explore_steps[purpose].pop(0)
                    if not explore_steps[purpose]:
                        del explore_steps[purpose]

                    print(f'Prompt: {step}')
                    return [step]

        # Default steps if none match
        return ["Look for exploits."]

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
        example_method = {}
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
                        if len(example_response) == 1:
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

    def transform_to_icl_with_previous_examples(self, init_steps: Dict) -> Dict:
        """
        Transforms penetration testing steps into in-context learning (ICL) prompts with previous example references.

        Args:
            init_steps (Dict[PromptPurpose, List[List[str]]]): A dictionary where each key is a PromptPurpose
                and each value is a list of steps.

        Returns:
            Dict[PromptPurpose, List[str]]: A dictionary where each key is a PromptPurpose and each value
                is a list of in-context learning prompts as strings, each with a reference to a previous example.
        """
        icl_prompts = {}

        for purpose, steps_groups in init_steps.items():
            prompts = []

            # Retrieve the previous example for the given purpose
            previous_example = self.response_history.get(purpose.name, None)

            for steps in steps_groups:
                for step in steps:
                    # Format the in-context learning prompt with the previous example and current step
                    if previous_example:
                        prompt = (
                            f"In a previous {purpose.name} test for endpoint {previous_example['step']}, "
                            f"the following step was used:\n"
                            f"- Step: \"{previous_example['step']}\"\n"
                            f"- Response: \"{previous_example['response']}\"\n\n"
                            f"For your current step on endpoint {step.split()[4]}:\n"
                            f"Step: \"{step}\"\n"
                            f"Expected Response: \"[Insert expected response based on step specifics]\""
                        )
                    else:
                        # If no example, just use the current step with expected response placeholder
                        prompt = (
                            f"For your current {purpose.name} step on endpoint {step.split()[4]}:\n"
                            f"Step: \"{step}\"\n"
                            f"Expected Response: \"[Insert expected response based on step specifics]\""
                        )

                    prompts.append(prompt)

            icl_prompts[purpose] = prompts

        return icl_prompts
