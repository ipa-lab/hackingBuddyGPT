import json
from typing import Dict, Optional, Any, List
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.utils.prompt_generation.prompts.state_learning.state_planning_prompt import (
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
                 open_api_spec: Any, prompt_file : Any=None) -> None:
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            context_information (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.IN_CONTEXT, prompt_file=prompt_file)
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
            turn (Optional[int]): Current turn.

        Returns:
            str: The generated prompt.
        """
        if self.context == PromptContext.DOCUMENTATION:
            steps = self._get_documentation_steps(move_type=move_type, previous_prompt=previous_prompt, doc_steps=self.get_documentation_steps())
        elif self.context == PromptContext.PENTESTING:
            steps = self._get_pentesting_steps(move_type=move_type)
        else:
            steps = self.parse_prompt_file()
            steps = self._get_documentation_steps(move_type=move_type, previous_prompt=previous_prompt,
                                                  doc_steps=steps)



        if hint:
            steps = steps + [hint]

        return self.prompt_helper._check_prompt(previous_prompt=previous_prompt, steps=steps)

    def _get_documentation_steps(self, move_type: str, previous_prompt, doc_steps: Any) -> List[str]:
        """
           Generates documentation steps based on the current API specification, previous prompts,
           and the intended move type.

           Args:
               move_type (str): Determines the strategy to apply. Accepted values:
                                - "explore": Generates initial documentation steps for exploration.
                                - Any other value: Triggers identification of endpoints needing more help.
               previous_prompt (Any): A history of previously generated prompts used to determine
                                      which endpoints have already been addressed.
               doc_steps (Any): Existing documentation steps that are modified or expanded based on
                                the selected move_type.

           Returns:
               List[str]: A list of documentation prompts tailored to the move_type and current context.
           """
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

        if move_type == "explore":
            icl = [[f"Based on this information :\n{icl_prompt}\n" + doc_steps[0][0]]]
            # if self.current_step == 0:
            #   self.current_step == 1
            doc_steps = icl + doc_steps[1:]
            # self.current_step += 1
            return self.prompt_helper.get_initial_documentation_steps(
                strategy_steps=doc_steps)
        else:
            return self.prompt_helper.get_endpoints_needing_help(
                info=f"Based on this information :\n{icl_prompt}\n Do the following: ")


    def extract_example_response(self, api_paths, endpoint, method="get"):
        """
           Extracts a representative example response for a specified API endpoint and method
           from an OpenAPI specification.
           Args:
               api_paths (dict): A dictionary representing the paths section of the OpenAPI spec,
                                 typically `self.open_api_spec["endpoints"]`.
               endpoint (str): The specific API endpoint to extract the example from (e.g., "/users").
               method (str, optional): The HTTP method to consider (e.g., "get", "post").
                                       Defaults to "get".

           Returns:
               dict: A dictionary with the HTTP method as the key and the extracted example
                     response as the value. If no suitable example is found, returns an empty dict.
                     Format: { "get": { "exampleName": exampleData } }
           """
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
                        if isinstance(example_details, dict):

                            example_value = example_details.get("value", {})
                            data = example_value.get("data", [])

                        else:
                            print(f'example_details: {example_details}')
                            example_value = example_details
                            data = example_details

                        if isinstance(data, list) and data != []:
                            data = data[0]
                        example_response[example_name] = data

                    example_method[method] = example_response

        return example_method

    # Function to generate the prompt for In-Context Learning
    def generate_icl_prompt(self, properties, example_response, endpoint):
        """
           Generates an in-context learning (ICL) prompt to guide a language model in understanding
           and documenting a REST API endpoint.

           Args:
               properties (dict): A dictionary of property names to their types and example values.
                                  Format: { "property_name": {"type": "string", "example": "value"} }
               example_response (dict): A dictionary containing example API responses, typically extracted
                                        using `extract_example_response`. Format: { "get": { ...example... } }
               endpoint (str): The API endpoint path (e.g., "/users").

           Returns:
               str: A formatted prompt string containing API metadata, property descriptions,
                    and a JSON-formatted example response.
           """
        # Core information about API
        if len(example_response.keys()) > 0:
            prompt = f"# REST API: {list(example_response.keys())[0].upper()} {endpoint}\n\n"
        else:
            prompt = f"# REST API: {endpoint}\n\n"


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
        """
            Extracts and flattens properties from a nested dictionary or list of dictionaries,
            producing a dictionary of property names along with their inferred types and example values.

            Args:
                data (dict or list): The input data, usually an example API response. This can be:
                    - A single dictionary (representing a single API object).
                    - A list of dictionaries (representing a collection of API objects).
                    - A special-case dict with a single `None` key, which is unwrapped.

            Returns:
                dict: A dictionary mapping property names to a dictionary with keys:
                      - "type": The inferred data type (e.g., "string", "integer").
                      - "example": A sample value for the property.
                      Format: { "property_name": {"type": "string", "example": "value"} }
            """

        # Handle nested dictionaries, return flattened properties

        if isinstance(data, dict) and len(data) == 1 and list(data.keys())[0] is None:
            data = list(data.values())[0]

        result = {}
        if isinstance(data, list):
            for item in data:
                result = self.get_props(item, result)


        else:
            result = self.get_props(data, result)

        return result


    def transform_into_prompt_structure_with_previous_examples(self, test_case, purpose):
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
            "assessments": [],
            "path": test_case.get("path")
        }


        # Process steps in the test case
        counter = 0
        for step in test_case["steps"]:
            if counter < len(test_case["security"]):
                security = test_case["security"][counter]
            else:
                security = test_case["security"][0]

            if len(test_case["steps"]) > 1:
                if counter <len(test_case["expected_response_code"]):
                    expected_response_code = test_case["expected_response_code"][counter]

                else:
                    expected_response_code = test_case["expected_response_code"]

                token = test_case["token"][counter]
                path = test_case["path"][counter]
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
            if "steps" not in test_case.keys():
                for step_details in test_case["step"]:
                        result.append(f"    {step_details['step']}\n")
                        result.append(f"Example: {self.get_properties(step_details)}")
            else:

                for idx, step_details in enumerate(test_case["steps"], start=0):
                    if len(test_case["steps"]) >1:
                        if self.counter == idx:
                            result.append(f"    {step_details['step']}\n")
                            result.append(f"Example: {self.get_properties(step_details)}")
                    else:
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

    def get_props(self, data:dict, result:dict ):
        """
          Recursively extracts properties from a dictionary, including nested dictionaries and lists,
          and appends them to the result dictionary with their inferred data types and example values.

          Returns:
              dict: The updated result dictionary containing all extracted properties, including those
                    found in nested dictionaries or lists.
          """

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


