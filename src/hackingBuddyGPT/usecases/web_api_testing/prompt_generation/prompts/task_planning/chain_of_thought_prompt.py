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

