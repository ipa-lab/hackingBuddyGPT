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
        self.current_step = 0
        self.explored_sub_steps =[]
        self.previous_purpose = None

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

        return self.prompt_helper._check_prompt(previous_prompt=previous_prompt, steps=steps)

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
            doc_steps = self.get_documentation_steps()
            icl = [[f"Based on this information :\n{icl_prompt}\n" + doc_steps[0][0]]]
            # if self.current_step == 0:
            #   self.current_step == 1
            doc_steps = icl + doc_steps[1:]
            # self.current_step += 1
            return self.prompt_helper._get_initial_documentation_steps(
                strategy_steps=doc_steps)
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

        if self.previous_purpose != self.purpose:
            self.previous_purpose = self.purpose
            if self.purpose != PromptPurpose.SETUP:
                self.pentesting_information.accounts = self.prompt_helper.accounts
        self.test_cases = self.pentesting_information.explore_steps(self.purpose)
        self.counter = 0

        purpose = self.purpose

        if move_type == "explore":
            test_cases = self.get_test_cases(self.test_cases)
            for test_case in test_cases:
                if purpose not in self.transformed_steps.keys():
                    self.transformed_steps[purpose] = []
                # Transform steps into icl based on purpose
                self.transformed_steps[purpose].append(
                    self.transform_to_icl_with_previous_examples(test_case, purpose)
                )

                # Extract the CoT for the current purpose
                icl_steps = self.transformed_steps[purpose]

                # Process steps one by one, with memory of explored steps and conditional handling
                for icl_test_case in icl_steps:
                    if icl_test_case not in self.explored_steps and not self.all_substeps_explored(icl_test_case):
                        self.current_step = icl_test_case
                        # single step test case
                        if len(icl_test_case.get("steps")) == 1:
                            self.current_sub_step = icl_test_case.get("steps")[0]
                        else:
                            # multi-step test case
                            self.current_sub_step = icl_test_case.get("steps")[self.counter]
                            self.explored_sub_steps.append(self.current_sub_step)
                        self.explored_steps.append(icl_test_case)


                        print(f'Current step: {self.current_step}')
                        print(f'Current sub step: {self.current_sub_step}')

                        self.prompt_helper.current_user = self.prompt_helper.get_user_from_prompt(self.current_sub_step)

                        step = self.transform_test_case_to_string(self.current_step, "steps")
                        self.counter += 1
                        # if last step of exploration, change purpose to next
                        self.next_purpose(icl_test_case, icl_steps, purpose)

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
                        data = example_value.get("data", [])
                        if data != []:
                            data = data[0]
                        example_response[example_name] = data

                    example_method[method] = example_response

        return example_method

    # Function to generate the prompt for In-Context Learning
    def generate_icl_prompt(self, properties, example_response, endpoint):
        # Core information about API
        prompt = f"# REST API: {example_response.keys()} {endpoint}\n\n"

        # Add properties to the prompt
        counter = 0
        if len(properties) == 0:
            properties = self.extract_properties_with_examples(example_response)
        for prop, details in properties.items():
            if counter == 0:
                prompt += "This API retrieves objects with the following properties:\n"
            prompt += f"- {prop}:{details['type']} (e.g., {details['example']})\n"
            counter += 1

        # Add an example response to the prompt
        prompt += "\nExample Response:\n`"
        if example_response != {}:
            example_key = list(example_response.keys())[0]  # Take the first example for simplicity
            example_json = json.dumps(example_response[example_key], indent=2)
            prompt += example_json

        return prompt

    def extract_properties_with_examples(self, data):

        # Handle nested dictionaries, return flattened properties

        if isinstance(data, dict) and len(data) == 1 and list(data.keys())[0] is None:
            data = list(data.values())[0]

        result = {}

        for key, value in data.items():

            if isinstance(value, dict):

                # Recursively extract properties from nested dictionaries

                nested_properties = self.extract_properties_with_examples(value)

                result.update(nested_properties)

            elif isinstance(value, list):

                if value:

                    example_value = value[0]

                    result[key] = {"type": "list", "example": example_value}

                else:

                    result[key] = {"type": "list", "example": "[]"}
            else:

                result[key] = {"type": type(value).__name__, "example": value}

        return result

    def sort_previous_prompt(self, previous_prompt):
        sorted_list = []
        for i in range(len(previous_prompt) - 1, -1, -1):
            sorted_list.append(previous_prompt[i])
        return sorted_list

    def transform_to_icl_with_previous_examples(self, test_case, purpose):
        """
            Transforms a single test case into a  In context learning structure.

            The transformation emphasizes breaking tasks into hierarchical phases and embedding conditional logic
            to adaptively handle outcomes, inspired by strategies in recent research on structured reasoning.

            Args:
                test_case (dict): A dictionary representing a single test case with fields like 'objective', 'steps', and 'security'.

            Returns:
                dict: A transformed test case structured hierarchically and conditionally.
        """

        # Initialize the transformed test case

        transformed_case = {
            "phase_title": f"Phase: {test_case['objective']}",
            "steps": [],
            "assessments": []
        }

        # Process steps in the test case
        counter = 0
        for step in test_case["steps"]:
            if len(test_case["security"]) > 1:
                security = test_case["security"][counter]
            else:
                security = test_case["security"][0]

            if len(test_case["steps"]) > 1:
                expected_response_code = test_case["expected_response_code"][counter]
                token = test_case["token"][counter]
                path = test_case[path][counter]
            else:
                expected_response_code = test_case["expected_response_code"]
                token = test_case["token"][0]
                path = test_case["path"][0]

            previous_example = self.response_history.get(purpose.name, None)
            if previous_example is not None:
                step = f"Previous example - Step: \"{previous_example['step']}\", Response: \"{previous_example['response']}\"" + step

            step_details = {
                "purpose": purpose,
                "step": step,
                "expected_response_code": expected_response_code,
                "security": security,
                "conditions": {
                    "if_successful": "No Vulnerability found.",
                    "if_unsuccessful": "Vulnerability found."
                },
                "token": token,
                "path": path
            }
            counter += 1
            transformed_case["steps"].append(step_details)

        # Add an assessment at the end of the phase
        transformed_case["assessments"].append(
            "Review all outcomes in this phase. If objectives are not met, revisit the necessary steps."
        )

        # Add a final assessment if applicable
        transformed_case["final_assessment"] = "Confirm that all objectives for this test case have been met."

        return transformed_case

    def extract_endpoints_from_prompts(self, step):
        endpoints = []
        # Extract endpoints from the text using simple keyword matching
        if isinstance(step, list):
            step = step[0]
        if "endpoint" in step.lower():
            words = step.split()
            for word in words:
                if word.startswith("https://") or word.startswith("/") and len(word) > 1:
                    endpoints.append(word)

        return list(set(endpoints))  # Return unique endpoints

    def transform_test_case_to_string(self, test_case, character):
        """
        Transforms a single test case into a formatted string representation.

        Args:
            test_case (dict): A dictionary representing a single test case transformed into a hierarchical structure.

        Returns:
            str: A formatted string representation of the test case.
        """
        # Initialize the result string
        result = []

        # Add the phase title
        result.append(f"{test_case['phase_title']}\n")

        # Add each step with conditions
        if character == "steps":
            for idx, step_details in enumerate(test_case["steps"], start=0):
                if self.counter == idx:
                    result.append(f"    {step_details['step']}\n")
                    result.append(f"Example: {self.get_properties(step_details)}")

        # Add phase assessments
        if character == "assessments":
            result.append("\nAssessments:\n")
            for assessment in test_case["assessments"]:
                result.append(f"  - {assessment}\n")

        # Add the final assessment if applicable
        if character == "final_assessment":
            if "final_assessment" in test_case:
                result.append(f"\nFinal Assessment:\n  {test_case['final_assessment']}\n")

        return ''.join(result)

    def get_properties(self, step_details):
        endpoints = self.extract_endpoints_from_prompts(step_details['step'])
        for endpoint in endpoints:
            for keys in self.pentesting_information.categorized_endpoints:
                for ep in self.pentesting_information.categorized_endpoints[keys]:

                    if ep["path"] == endpoint:
                        print(f'ep:{ep}')
                        print(f' endpoint: {endpoint}')
                        properties = ep.get('schema', {}).get('properties', {})
                        return properties

    def next_purpose(self, step, icl_steps, purpose):
        # Process the step and return its result
        last_item = icl_steps[-1]
        if step == last_item:
            # If it's the last step, remove the purpose and update self.purpose
            if purpose in self.pentesting_information.pentesting_step_list:
                self.pentesting_information.pentesting_step_list.remove(purpose)
            if self.pentesting_information.pentesting_step_list:
                self.purpose = self.pentesting_information.pentesting_step_list[0]

        self.counter = 0 # Reset counter

    def all_substeps_explored(self, icl_steps):
        all_steps = []
        for step in icl_steps.get("steps") :
            all_steps.append(step)

        if all_steps in self.explored_sub_steps:
            return True
        else:
            return False



