from typing import List, Optional
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.utils.prompt_generation.prompts.task_planning.task_planning_prompt import (
    TaskPlanningPrompt,
)


class ChainOfThoughtPrompt(TaskPlanningPrompt):
    """
    A class that generates prompts using the chain-of-thought strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    chain-of-thought strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        explored_steps (List[str]): A list of steps that have already been explored in the chain-of-thought strategy.
    """

    def __init__(self, context: PromptContext, prompt_helper, prompt_file):
        """
        Initializes the ChainOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.CHAIN_OF_THOUGHT, prompt_file= prompt_file)
        self.counter = 0

    def generate_prompt(
            self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Generates a prompt using the chain-of-thought strategy. Provides the steps for the chain-of-thought strategy based on the current context.
        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (Optional[str]): The previous prompt content based on the conversation history.
            turn (Optional[int]): The current turn of the chain-of-thought strategy.

        Returns:
            str: The generated prompt.
        """
        if self.context == PromptContext.DOCUMENTATION:
            self.purpose = PromptPurpose.DOCUMENTATION
            chain_of_thought_steps = self._get_documentation_steps([],move_type, self.get_documentation_steps())
            chain_of_thought_steps = [chain_of_thought_steps[0]] + [
                "Let's think step by step"] + chain_of_thought_steps[1:]

        elif self.context == PromptContext.PENTESTING:
            chain_of_thought_steps = self._get_pentesting_steps(move_type,"")
        else:
            steps = self.parse_prompt_file()
            chain_of_thought_steps = self._get_documentation_steps([],move_type, steps)

            chain_of_thought_steps = [chain_of_thought_steps[0]] + [
                "Let's think step by step"] + chain_of_thought_steps[1:]
        if hint:
            chain_of_thought_steps.append(hint)

        return self.prompt_helper._check_prompt(previous_prompt=previous_prompt, steps=chain_of_thought_steps)

    def get_documentation_steps(self):
        """
        Returns a predefined list of endpoint exploration steps based on the target API host.

        These steps are used to guide automated documentation of a web API by progressively
        discovering and querying endpoints using GET requests. The process follows a structured
        hierarchy from root-level endpoints to more complex nested endpoints and those with query parameters.

        Returns:
            List[List[str]]: A list of steps, each step being a list of instruction strings.
        """

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


    def transform_into_prompt_structure(self, test_case, purpose):
        """
            Transforms a single test case into a Hierarchical-Conditional Hybrid Chain-of-Prompt structure.

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
        #print(f' test case:{test_case}')
        for step in test_case["steps"]:
            if counter < len(test_case["security"]):
                security = test_case["security"][counter]
            else:
                security = test_case["security"][0]

            if len(test_case["steps"]) > 1:
                if counter < len(test_case["expected_response_code"]):
                    expected_response_code = test_case["expected_response_code"][counter]

                else:
                    expected_response_code = test_case["expected_response_code"]

                token = test_case["token"][counter]
                path = test_case["path"][counter]
            else:
                expected_response_code = test_case["expected_response_code"]
                token = test_case["token"][0]
                path = test_case["path"][0]

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
            result.append("Let's think step by step.")
            result.append("Steps:\n")
            for idx, step_details in enumerate(test_case["steps"], start=1):
                result.append(f"  Step {idx}:\n")
                result.append(f"    {step_details['step']}\n")

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

    def generate_documentation_steps(self, steps) -> list:
        """
        Creates a chain of thought prompt to guide the model through the API documentation process.

        Args:
        steps (list): A list of steps, where each step is a list. The first element
                      of each inner list is the step title, followed by its sub-steps or details.

    Returns:
        list: A transformed list where each step (except the first) is prefixed with
              "Step X:" headers and includes its associated sub-steps.
        """

        transformed_steps = [steps[0]]

        for index, steps in enumerate(steps[1:], start=1):
            step_header = f"Step {index}: {steps[0]}"
            detailed_steps = steps[1:]
            transformed_step = [step_header] + detailed_steps
            transformed_steps.append(transformed_step)

        return transformed_steps
