from typing import List, Optional

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
        purpose (Optional[PromptPurpose]): The purpose of the current prompt.
    """

    def __init__(self, context: PromptContext, prompt_helper):
        """
        Initializes the ChainOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.CHAIN_OF_THOUGHT)
        self.explored_steps: List[str] = []
        self.purpose: Optional[PromptPurpose] = None

    def generate_prompt(
        self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Generates a prompt using the chain-of-thought strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (Optional[str]): The previous prompt content based on the conversation history.

        Returns:
            str: The generated prompt.
        """
        common_steps = self._get_common_steps()
        chain_of_thought_steps = self._get_chain_of_thought_steps(common_steps, move_type)

        if hint:
            chain_of_thought_steps.append(hint)

        return self.prompt_helper.check_prompt(previous_prompt=previous_prompt, steps=chain_of_thought_steps)

    def _get_common_steps(self) -> List[str]:
        """
        Provides a list of common steps for generating prompts.

        Returns:
            List[str]: A list of common steps for generating prompts.
        """
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

    def _get_chain_of_thought_steps(self, common_steps: List[str], move_type: str) -> List[str]:
        """
        Provides the steps for the chain-of-thought strategy based on the current context.

        Args:
            common_steps (List[str]): A list of common steps for generating prompts.
            move_type (str): The type of move to generate.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy.
        """
        if self.context == PromptContext.DOCUMENTATION:
            self.purpose = PromptPurpose.DOCUMENTATION
            return self._get_documentation_steps(common_steps, move_type)
        else:
            return self._get_pentesting_steps(move_type)

    def _get_documentation_steps(self, common_steps: List[str], move_type: str) -> List[str]:
        """
        Provides the steps for the chain-of-thought strategy when the context is documentation.

        Args:
            common_steps (List[str]): A list of common steps for generating prompts.
            move_type (str): The type of move to generate.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the documentation context.
        """
        if move_type == "explore":
            return self.prompt_helper.get_initial_steps(common_steps)
        else:
            return self.prompt_helper.get_endpoints_needing_help()

    def _get_pentesting_steps(self, move_type: str) -> List[str]:
        """
        Provides the steps for the chain-of-thought strategy when the context is pentesting.

        Args:
            move_type (str): The type of move to generate.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the pentesting context.
        """
        if move_type == "explore":
            purpose = list(self.pentesting_information.explore_steps.keys())[0]
            step = self.pentesting_information.explore_steps[purpose]
            if step not in self.explored_steps:
                if len(step) > 1:
                    step = self.pentesting_information.explore_steps[purpose][0]
                    if len(self.pentesting_information.explore_steps[purpose]) == 0:
                        del self.pentesting_information.explore_steps[purpose][0]
                prompt = step
                self.purpose = purpose
                self.explored_steps.append(step)
                if len(step) == 1:
                    del self.pentesting_information.explore_steps[purpose]

                print(f"prompt: {prompt}")
                return prompt
        else:
            return ["Look for exploits."]
