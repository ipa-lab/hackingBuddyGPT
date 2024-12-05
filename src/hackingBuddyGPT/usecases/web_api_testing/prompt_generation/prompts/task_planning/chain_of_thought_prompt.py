from typing import List, Optional, Tuple, Any
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.task_planning.task_planning_prompt import (
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

    def __init__(self, context: PromptContext, prompt_helper):
        """
        Initializes the ChainOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.CHAIN_OF_THOUGHT)
        self.phase = None
        self.transformed_steps = {}
        self.pentest_steps = None

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
        common_steps = self._get_common_steps()
        if self.context == PromptContext.DOCUMENTATION:
            self.purpose = PromptPurpose.DOCUMENTATION
            chain_of_thought_steps = self._get_documentation_steps(common_steps, move_type)
        else:
            chain_of_thought_steps = self._get_pentesting_steps(move_type)
        if hint:
            chain_of_thought_steps.append(hint)

        return self.prompt_helper.check_prompt(previous_prompt=previous_prompt, steps=chain_of_thought_steps)

    def _get_pentesting_steps(self, move_type: str, common_step: Optional[str] = "") -> Any:
        """
        Provides the steps for the chain-of-thought strategy when the context is pentesting.

        Args:
            move_type (str): The type of move to generate.
            common_step (Optional[str]): A list of common steps for generating prompts.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the pentesting context.
        """
        if self.pentest_steps == None:
            self.pentest_steps = self.pentesting_information.explore_steps()

        purpose = self.purpose
        test_cases = self.pentesting_information.get_steps_of_phase(purpose, self.pentest_steps)
        if move_type == "explore":

            if purpose not in self.transformed_steps.keys():
                for test_case in test_cases:
                    if purpose not in self.transformed_steps.keys():
                        self.transformed_steps[purpose] = []
                    # Transform steps into hierarchical conditional CoT based on purpose
                    self.transformed_steps[purpose].append(
                        self.transform_to_hierarchical_conditional_cot(test_case, purpose))

            # Extract the CoT for the current purpose
            cot_steps = self.transformed_steps[purpose]

            # Process steps one by one, with memory of explored steps and conditional handling
            for step in cot_steps:
                if step not in self.explored_steps:
                    self.explored_steps.append(step)
                    print(f'Prompt: {step}')
                    self.current_step = step
                    # Process the step and return its result
                    last_item = cot_steps[-1]
                    if step == last_item:
                        # If it's the last step, remove the purpose and update self.purpose
                        if purpose in self.pentesting_information.pentesting_step_list:
                            self.pentesting_information.pentesting_step_list.remove(purpose)
                        if self.pentesting_information.pentesting_step_list:
                            self.purpose = self.pentesting_information.pentesting_step_list[0]
                    step = self.transform_test_case_to_string(step, "steps")

                    return [step]



        else:
            return ["Look for exploits."]

    def transform_to_hierarchical_conditional_cot(self, test_case, purpose):
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
            else:
                expected_response_code = test_case["expected_response_code"]

            step_details = {
                "purpose": purpose,
                "step": step,
                "expected_response_code": expected_response_code,
                "security": security,
                "conditions": {
                    "if_successful": "No Vulnerability found.",
                    "if_unsuccessful": "Vulnerability found."
                }
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

    def generate_documentation_steps(self, steps) -> list:
        """
        Creates a chain of thought prompt to guide the model through the API documentation process.

        Args:
            use_token (str): A string indicating whether authentication is required.
            endpoints (list): A list of endpoints to exclude from testing.

        Returns:
            str: A structured chain of thought prompt for documentation.
        """

        transformed_steps = [steps[0]]

        for index, steps in enumerate(steps[1:], start=1):
            step_header = f"Step {index}: {steps[0]}"
            detailed_steps = steps[1:]
            transformed_step = [step_header] + detailed_steps
            transformed_steps.append(transformed_step)

        return transformed_steps

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
