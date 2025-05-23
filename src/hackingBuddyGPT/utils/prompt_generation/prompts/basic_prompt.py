import os.path
from abc import ABC, abstractmethod
from typing import Optional, Any
from hackingBuddyGPT.utils.prompt_generation.information import (
    PenTestingInformation,
)
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
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
            prompt_file: Any =None
    ):
        """
        Initializes the BasicPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            planning_type (PlanningType): The type of planning.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The strategy used for prompt generation.
        """
        self.transformed_steps = {}
        self.open_api_spec = {}
        self.context = context
        if context is None:
            if os.path.exists(prompt_file):
                self.prompt_file = prompt_file
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
        return [
            [
                f"Objective: Identify all accessible endpoints via GET requests for {self.prompt_helper.host}. {self.prompt_helper._description}"],
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
        """
           Extracts example values and data types from the 'Post' schema in the OpenAPI specification.

           This method reads the OpenAPI spec's components → schemas → Post → properties, and
           gathers relevant information like example values and types for each property defined.

           Returns:
               dict: A dictionary mapping property names to their example values and types.
                     Format: { prop_name: {"example": str, "type": str} }
           """
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
        """
           Reverses the order of a list of previous prompts.

           This function takes a list of prompts (e.g., user or system instructions)
           and returns a new list with the elements in reverse order, placing the most
           recent prompt first.

           Parameters:
               previous_prompt (list): A list of prompts in chronological order (oldest first).

           Returns:
               list: A new list containing the prompts in reverse order (most recent first).
           """
        sorted_list = []
        for i in range(len(previous_prompt) - 1, -1, -1):
            sorted_list.append(previous_prompt[i])
        return sorted_list

    def parse_prompt_file(self):
        with open(self.prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = content.strip().split('---')
        prompt_blocks = []

        for block in blocks:
            block = block.replace("{host}", self.prompt_helper.host).replace("{description}", self.prompt_helper._description)
            lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
            if lines:
                prompt_blocks.append(lines)

        return prompt_blocks

    def extract_endpoints_from_prompts(self, step):
        """
          Extracts potential endpoint paths or URLs from a prompt step.

          This method scans the provided step (either a string or a list containing a string),
          and attempts to identify words that represent API endpoints — such as relative paths
          (e.g., '/users') or full URLs (e.g., 'https://example.com/users') — using simple keyword
          heuristics and filtering.

          Parameters:
              step (str or list): A prompt step that may contain one or more textual instructions,
                                  possibly with API endpoint references.

          Returns:
              list: A list of unique endpoint strings extracted from the step.
          """
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
        """
           Extracts the schema properties of an endpoint mentioned in a given step.

           This function analyzes a prompt step, extracts referenced API endpoints,
           and searches the stored categorized endpoints to find a matching one.
           If a match is found and it contains a schema with defined properties,
           those properties are returned.

           Parameters:
               step_details (dict): A dictionary containing step information.
                                    It is expected to include a key 'step' with either a string
                                    or list of strings that describe the test step.

           Returns:
               dict or None: A dictionary of properties from the matched endpoint's schema,
                             or None if no match is found or no schema is available.
           """
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
        """
          Updates the current pentesting purpose based on the progress of ICL steps.

          If the current purpose has no test cases left (`icl_steps` is None), it is removed from
          the list of remaining purposes. Otherwise, if the current `step` matches the last explored
          step, it also considers the current purpose complete and advances to the next one.

          Parameters:
              step (dict or None): The current step being evaluated.
              icl_steps (list or None): A list of previously explored steps.
              purpose (str): The current pentesting purpose associated with the step.

          Returns:
              None
          """
        # Process the step and return its result
        if icl_steps is None:
            self.pentesting_information.pentesting_step_list.remove(purpose)
            self.purpose = self.pentesting_information.pentesting_step_list[0]
            self.counter = 0 # Reset counter
            return
        last_item = icl_steps[-1]
        if self.check_if_step_is_same(last_item, step) or step is None:
            # If it's the last step, remove the purpose and update self.purpose
            if purpose in self.pentesting_information.pentesting_step_list:
                self.pentesting_information.pentesting_step_list.remove(purpose)
            if self.pentesting_information.pentesting_step_list:
                self.purpose = self.pentesting_information.pentesting_step_list[0]

            self.counter = 0 # Reset counter

    def check_if_step_is_same(self, step1, step2):
        """
            Compares two step dictionaries to determine if they represent the same step.

            Specifically checks if the first item in the 'steps' list of `step1` is equal to
            the 'step' value of the first item in the 'steps' list of `step2`.

            Parameters:
                step1 (dict): The first step to compare.
                step2 (dict): The second step to compare.

            Returns:
                bool: True if both steps are considered the same, False otherwise.
            """
        # Check if 'steps' and 'path' are identical
        steps_same = (step1.get('steps', [])[0] == step2.get('steps', [])[0].get("step"))

        return steps_same
    def all_substeps_explored(self, icl_steps):

        """
            Checks whether all substeps in the provided ICL step block have already been explored.

            Compares the list of substeps in `icl_steps` against the `explored_sub_steps` list
            to determine if they were previously processed.

            Parameters:
                icl_steps (dict): A dictionary containing a list of steps under the 'steps' key.

            Returns:
                bool: True if all substeps were explored, False otherwise.
            """
        all_steps = []
        for step in icl_steps.get("steps") :
            all_steps.append(step)

        if all_steps in self.explored_sub_steps:
            return True
        else:
            return False


    def reset_accounts(self):
        self.prompt_helper.accounts = [acc for acc in self.prompt_helper.accounts if "x" in acc and acc["x"] != ""]

    def get_test_cases(self, test_cases):
        """
            Attempts to retrieve a valid list of test cases.

            This method first checks if the input `test_cases` is an empty list.
            If so, it iterates through the pentesting step list and attempts to fetch
            non-empty test cases using `get_steps_of_phase`, skipping any already transformed steps.

            If no valid test cases are found or if `test_cases` is None, it will repeatedly call
            `next_purpose()` and use `explore_steps()` until it retrieves a non-None result.

            Parameters:
                test_cases (list or None): An initial set of test cases to validate or replace.

            Returns:
                list or None: A valid list of test cases or None if none could be retrieved.
            """
        # If test_cases is an empty list, try to find a new non-empty list from other phases
        while isinstance(test_cases, list) and len(test_cases) == 0:
            for purpose in self.pentesting_information.pentesting_step_list:
                if purpose in self.transformed_steps.keys():
                    continue
                else:
                    test_cases = self.pentesting_information.get_steps_of_phase(purpose)
                    if test_cases is not None:
                        if len(test_cases) != 0:
                            return test_cases

        # If test_cases is None, keep trying next_purpose and explore_steps until something is found
        if test_cases is None:
            while test_cases is None:
                self.next_purpose(None, test_cases, self.purpose)
                test_cases = self.pentesting_information.explore_steps(self.purpose)

        return test_cases
