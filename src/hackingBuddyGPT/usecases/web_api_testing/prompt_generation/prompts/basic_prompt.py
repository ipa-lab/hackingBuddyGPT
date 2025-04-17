from abc import ABC, abstractmethod
from typing import Optional
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import (
    PenTestingInformation,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy, PromptPurpose,
)


class BasicPrompt(ABC):
    """
    Abstract base class for generating prompts based on different strategies and contexts.

    This class serves as a blueprint for creating specific prompt generators that operate under different strategies,
    such as chain-of-thought or simple prompt generation strategies, tailored to different contexts like documentation
    or pentesting.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        strategy (PromptStrategy): The strategy used for prompt generation.
        pentesting_information (Optional[PenTestingInformation]): Contains information relevant to pentesting when the context is pentesting.
    """

    def __init__(
            self,
            context: PromptContext = None,
            planning_type: PlanningType = None,
            prompt_helper=None,
            strategy: PromptStrategy = None,
    ):
        """
        Initializes the BasicPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            planning_type (PlanningType): The type of planning.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The strategy used for prompt generation.
        """
        self.context = context
        self.planning_type = planning_type
        self.prompt_helper = prompt_helper
        self.strategy = strategy
        self.current_step = 0
        self.explored_sub_steps = []
        self.previous_purpose = None
        self.counter = 0

    def set_pentesting_information(self, pentesting_information: PenTestingInformation):
        self.pentesting_information = pentesting_information
        self.purpose = self.pentesting_information.pentesting_step_list[0]
        self.previous_purpose = PromptPurpose.SETUP
        self.test_cases = self.pentesting_information.explore_steps(self.previous_purpose)

    @abstractmethod
    def generate_prompt(
            self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Abstract method to generate a prompt.

        This method must be implemented by subclasses to generate a prompt based on the given move type, optional hint, and previous prompt.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (Optional[str]): The previous prompt content based on the conversation history.
            turn (Optional[int]): The current turn

        Returns:
            str: The generated prompt.
        """
        pass

    def get_documentation_steps(self):

        # Define specific documentation steps based on the given strategy
         return [
            [f"Objective: Identify all accessible endpoints via GET requests for {self.prompt_helper.host}. {self.prompt_helper._description}"],
            [
                f""" Query root-level resource endpoints.
                               Find root-level endpoints for {self.prompt_helper.host}.
                               Only send GET requests to root-level endpoints with a single path component after the root. This means each path should have exactly one '/' followed by a single word (e.g., '/users', '/products').  
                               1. Send GET requests to new paths only, avoiding any in the lists above.
                               2. Do not reuse previously tested paths."""

            ],
            [
                "Query Instance-level resource endpoint with id",
                "Look for Instance-level resource endpoint : Identify endpoints of type `/resource/id` where id is the parameter for the id.",
                "Query these `/resource/id` endpoints to see if an `id` parameter resolves the request successfully."
                "Ids can be integers, longs or base62."

            ],
            [
                "Query Subresource Endpoints",
                "Identify subresource endpoints of the form `/resource/other_resource`.",
                "Query these endpoints to check if they return data related to the main resource without requiring an `id` parameter."


            ],

            [
                "Query for related resource endpoints",
                "Identify related resource endpoints that match the format `/resource/id/other_resource`: "
                f"First, scan for the follwoing endpoints where an `id` in the middle position and follow them by another resource identifier.",
                "Second, look for other endpoints and query these endpoints with appropriate `id` values to determine their behavior and document responses or errors."
            ],
            [
                "Query multi-level resource endpoints",
                "Search for multi-level endpoints of type `/resource/other_resource/another_resource`: Identify any endpoints in the format with three resource identifiers.",
                "Test requests to these endpoints, adjusting resource identifiers as needed, and analyze responses to understand any additional parameters or behaviors."
            ],
            [
                "Query endpoints with query parameters",
                "Construct and make GET requests to these endpoints using common query parameters (e.g. `/resource?param1=1&param2=3`) or based on documentation hints, testing until a valid request with query parameters is achieved."
            ]
        ]
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

    def sort_previous_prompt(self, previous_prompt):
        sorted_list = []
        for i in range(len(previous_prompt) - 1, -1, -1):
            sorted_list.append(previous_prompt[i])
        return sorted_list


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



    def get_properties(self, step_details):
        endpoints = self.extract_endpoints_from_prompts(step_details['step'])
        for endpoint in endpoints:
            for keys in self.pentesting_information.categorized_endpoints:
                for ep in self.pentesting_information.categorized_endpoints[keys]:
                    print(f'ep:{ep}')

                    if ep["path"] == endpoint:
                        print(f'ep:{ep}')
                        print(f' endpoint: {endpoint}')
                        schema = ep.get('schema', {})
                        if schema != None and schema != {}:
                            properties = schema.get('properties', {})
                        else:
                            properties = None
                        return properties

    def next_purpose(self, step, icl_steps, purpose):
        # Process the step and return its result
        last_item = icl_steps[-1]
        if self.check_if_step_is_same(last_item, step):
            # If it's the last step, remove the purpose and update self.purpose
            if purpose in self.pentesting_information.pentesting_step_list:
                self.pentesting_information.pentesting_step_list.remove(purpose)
            if self.pentesting_information.pentesting_step_list:
                self.purpose = self.pentesting_information.pentesting_step_list[0]

            self.counter = 0 # Reset counter
            print(f'purpose:{self.purpose}')

    def check_if_step_is_same(self, step1, step2):
        # Check if 'steps' and 'path' are identical
        steps_same = (step1.get('steps', [])[0] == step2.get('steps', [])[0].get("step"))

        return steps_same
    def all_substeps_explored(self, icl_steps):
        all_steps = []
        for step in icl_steps.get("steps") :
            all_steps.append(step)

        if all_steps in self.explored_sub_steps:
            return True
        else:
            return False

    def get_props(self, data, result ):
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

    def reset_accounts(self):
        self.prompt_helper.accounts = [acc for acc in self.prompt_helper.accounts if "x" in acc and acc["x"] != ""]