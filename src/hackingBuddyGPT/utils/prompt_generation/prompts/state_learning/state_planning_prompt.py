from abc import abstractmethod
from typing import List, Any

from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy, PromptPurpose,
)
from hackingBuddyGPT.utils.prompt_generation.prompts import (
    BasicPrompt,
)


class StatePlanningPrompt(BasicPrompt):
    """
    A class for generating state planning prompts, including strategies like In-Context Learning (ICL).

    This class extends BasicPrompt to provide specific implementations for state planning strategies, focusing on
    adapting prompts based on the current context or state of information provided.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        strategy (PromptStrategy): The strategy used for prompt generation, typically state-oriented like ICL.
        pentesting_information (Optional[PenTestingInformation]): Contains information relevant to pentesting when the context is pentesting.
    """

    def __init__(self, context: PromptContext, prompt_helper, strategy: PromptStrategy, prompt_file: Any=None):
        """
        Initializes the StatePlanningPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The state planning strategy used for prompt generation.
        """
        super().__init__(
            context=context,
            planning_type=PlanningType.STATE_PLANNING,
            prompt_helper=prompt_helper,
            strategy=strategy,
            prompt_file=prompt_file
        )
        self.explored_steps: List[str] = []
        self.transformed_steps ={}

    def set_pentesting_information(self, pentesting_information: PenTestingInformation):
        self.pentesting_information = pentesting_information
        self.purpose = self.pentesting_information.pentesting_step_list[0]
        self.pentesting_information.next_testing_endpoint()


    def _get_pentesting_steps(self, move_type: str) -> List[str]:
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
            self.reset_accounts()
            self.test_cases = self.pentesting_information.explore_steps(self.purpose)
            if self.purpose == PromptPurpose.SETUP:
                if self.counter == 0:
                    self.prompt_helper.accounts = self.pentesting_information.accounts
            else:
                self.pentesting_information.accounts = self.prompt_helper.accounts

        else:

            self.prompt_helper.accounts = self.pentesting_information.accounts
        purpose = self.purpose

        if move_type == "explore":
            test_cases = self.get_test_cases(self.test_cases)
            for test_case in test_cases:
                if purpose not in self.transformed_steps.keys():
                    self.transformed_steps[purpose] = []
                # Transform steps into icl based on purpose
                self.transformed_steps[purpose].append(
                    self.transform_into_prompt_structure_with_previous_examples(test_case, purpose)
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
                            self.current_sub_step["path"] = icl_test_case.get("path")[0]
                        else:
                            if self.counter < len(icl_test_case.get("steps")):
                                # multi-step test case
                                self.current_sub_step = icl_test_case.get("steps")[self.counter]
                                if len(icl_test_case.get("path")) > 1:
                                    self.current_sub_step["path"] = icl_test_case.get("path")[self.counter]
                            self.explored_sub_steps.append(self.current_sub_step)
                        self.explored_steps.append(icl_test_case)

                        self.prompt_helper.current_user = self.prompt_helper.get_user_from_prompt(self.current_sub_step, self.pentesting_information.accounts)
                        self.prompt_helper.counter = self.counter



                        step = self.transform_test_case_to_string(self.current_step, "steps")
                        if self.prompt_helper.current_user is not None or isinstance(self.prompt_helper.current_user,
                                                                                     dict):
                            if "token" in self.prompt_helper.current_user and "'{{token}}'" in step:
                                step = step.replace("'{{token}}'", self.prompt_helper.current_user.get("token"))
                        self.counter += 1
                        # if last step of exploration, change purpose to next
                        self.next_purpose(icl_test_case,test_cases, purpose)

                        return [step]

        # Default steps if none match
        return ["Look for exploits."]


    @abstractmethod
    def transform_into_prompt_structure_with_previous_examples(self, test_case, purpose):
        pass
    @abstractmethod
    def transform_test_case_to_string(self, current_step, param):
        pass