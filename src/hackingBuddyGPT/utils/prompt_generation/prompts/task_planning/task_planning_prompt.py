from abc import abstractmethod

from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy,
    PromptPurpose,
)
from hackingBuddyGPT.utils.prompt_generation.prompts import (
    BasicPrompt,
)

from typing import List, Optional, Any


class TaskPlanningPrompt(BasicPrompt):
    """
    A class for generating task planning prompts, including strategies like Chain-of-Thought (CoT) and Tree-of-Thought (ToT).

    This class extends BasicPrompt to provide specific implementations for task planning strategies, allowing for
    detailed step-by-step reasoning or exploration of multiple potential reasoning paths.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        strategy (PromptStrategy): The strategy used for prompt generation, which could be CoT, ToT, etc.
        pentesting_information (Optional[PenTestingInformation]): Contains information relevant to pentesting when the context is pentesting.
    """

    def __init__(self, context: PromptContext, prompt_helper, strategy: PromptStrategy, prompt_file : Any=None):
        """
        Initializes the TaskPlanningPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The task planning strategy used for prompt generation.
        """
        super().__init__(
            context=context,
            planning_type=PlanningType.TASK_PLANNING,
            prompt_helper=prompt_helper,
            strategy=strategy,
            prompt_file= prompt_file
        )
        self.explored_steps: List[str] = []
        self.purpose: Optional[PromptPurpose] = None
        self.phase = None
        self.transformed_steps = {}
        self.pentest_steps = None

    def _get_documentation_steps(self, common_steps: List[str], move_type: str, steps: Any) -> List[str]:
        """
        Provides the steps for the task learning prompt when the context is documentation.

        Args:
            common_steps (List[str]): A list of common steps for generating prompts.
            move_type (str): The type of move to generate.
            steps (Any): steps that are transformed into task planning prompt

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the documentation context.
        """
        if move_type == "explore":
            doc_steps = self.generate_documentation_steps(steps)
            return self.prompt_helper.get_initial_documentation_steps(
                                                                       strategy_steps= doc_steps)
        else:
            return self.prompt_helper.get_endpoints_needing_help()

    def _get_pentesting_steps(self, move_type: str, common_step: Optional[str] = "") -> Any:
        """
        Provides the steps for the chain-of-thought strategy when the context is pentesting.

        Args:
            move_type (str): The type of move to generate.
            common_step (Optional[str]): A list of common steps for generating prompts.

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
                    self.transform_into_prompt_structure(test_case, purpose)
                )

                # Extract the Task planning test cases for the current purpose
                task_planning_test_cases = self.transformed_steps[purpose]

                # Process steps one by one, with memory of explored steps and conditional handling
                for task_planning_test_case in task_planning_test_cases:
                    if task_planning_test_case not in self.explored_steps and not self.all_substeps_explored(task_planning_test_case):
                        self.current_step = task_planning_test_case
                        # single step test case
                        if len(task_planning_test_case.get("steps")) == 1:
                            self.current_sub_step = task_planning_test_case.get("steps")[0]
                            self.current_sub_step["path"] = task_planning_test_case.get("path")[0]
                        else:
                            if self.counter < len(task_planning_test_case.get("steps")):
                                # multi-step test case
                                self.current_sub_step = task_planning_test_case.get("steps")[self.counter]
                                if len(task_planning_test_case.get("path")) > 1:
                                    self.current_sub_step["path"] = task_planning_test_case.get("path")[self.counter]
                            self.explored_sub_steps.append(self.current_sub_step)
                        self.explored_steps.append(task_planning_test_case)



                        self.prompt_helper.current_user = self.prompt_helper.get_user_from_prompt(self.current_sub_step,
                                                                                                  self.pentesting_information.accounts)

                        self.prompt_helper.counter = self.counter

                        step = self.transform_test_case_to_string(self.current_step, "steps")

                        if self.prompt_helper.current_user is not None or isinstance(self.prompt_helper.current_user,dict):
                            if "token" in self.prompt_helper.current_user and "'{{token}}'" in step:
                                step = step.replace("'{{token}}'", self.prompt_helper.current_user.get("token"))

                        self.counter += 1
                        # if last step of exploration, change purpose to next
                        self.next_purpose(task_planning_test_case, test_cases, purpose)

                        return [step]

        # Default steps if none match
        return ["Look for exploits."]


    def _get_common_steps(self) -> List[str]:
        """
        Provides a list of common steps for generating prompts.

        Returns:
            List[str]: A list of common steps for generating prompts.

        """
        if self.strategy == PromptStrategy.CHAIN_OF_THOUGHT:
            if self.context == PromptContext.DOCUMENTATION:
                return [
                    "Identify common data structures returned by various endpoints and define them as reusable schemas. "
                    "Determine the type of each field (e.g., integer, string, array) and define common response structures as components that can be referenced in multiple endpoint definitions.",
                    "Create an OpenAPI document including metadata such as API title, version, and description, define the base URL of the API, list all endpoints, methods, parameters, and responses, and define reusable schemas, response types, and parameters.",
                    "Ensure the correctness and completeness of the OpenAPI specification by validating the syntax and completeness of the document using tools like Swagger Editor, and ensure the specification matches the actual behavior of the API.",
                    "Refine the document based on feedback and additional testing, share the draft with others, gather feedback, and make necessary adjustments. Regularly update the specification as the API evolves.",
                    "Make the OpenAPI specification available to developers by incorporating it into your API documentation site and keep the documentation up to date with API changes.",
                ]
            else:
                return [
                    "Identify common data structures returned by various endpoints and define them as reusable schemas, specifying field types like integer, string, and array.",
                    "Create an OpenAPI document that includes API metadata (title, version, description), the base URL, endpoints, methods, parameters, and responses.",
                    "Ensure the document's correctness and completeness using tools like Swagger Editor, and verify it matches the API's behavior. Refine the document based on feedback, share drafts for review, and update it regularly as the API evolves.",
                    "Make the specification available to developers through the API documentation site, keeping it current with any API changes.",
                ]
        elif self.strategy == PromptStrategy.TREE_OF_THOUGHT:
            if self.context == PromptContext.DOCUMENTATION:
                return [
                    "Imagine three different OpenAPI specification specialists.\n"
                    "All experts will write down one step of their thinking,\n"
                    "then share it with the group.\n"
                    "After that, all remaining specialists will proceed to the next step, and so on.\n"
                    "If any specialist realizes they're wrong at any point, they will leave.\n"
                    f"The question is: "

                ]
            else:
                return [
                    "Imagine three different Pentest experts are answering this question.\n"
                    "All experts will write down one step of their thinking,\n"
                    "then share it with the group.\n"
                    "After that, all experts will proceed to the next step, and so on.\n"
                    "If any expert realizes they're wrong at any point, they will leave.\n"
                    f"The question is: "
                ]

        else:
            raise TypeError(f"There exists no PromptStrategy of the type {self.strategy}")

    @abstractmethod
    def generate_documentation_steps(self, steps: List[str]) -> List[str] :
        pass


    @abstractmethod
    def transform_test_case_to_string(self, current_step, param):
        pass

    @abstractmethod
    def transform_into_prompt_structure(self, test_case, purpose):
        pass

