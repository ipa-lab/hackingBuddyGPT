from typing import Optional

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.task_planning import (
    TaskPlanningPrompt,
)
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Prompt


class TreeOfThoughtPrompt(TaskPlanningPrompt):
    """
    A class that generates prompts using the tree-of-thought strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    tree-of-thought strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        rest_api (str): The REST API endpoint for which prompts are generated.
        round (int): The round number for the prompt generation process.
        purpose (Optional[PromptPurpose]): The purpose of the prompt generation, which can be set during the process.
    """

    def __init__(self, context: PromptContext, prompt_helper, rest_api: str) -> None:
        """
        Initializes the TreeOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            rest_api (str): The REST API endpoint.
            round (int): The round number for the prompt generation process.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.TREE_OF_THOUGHT)
        self.rest_api: str = rest_api

    def generate_prompt(self, move_type: str, hint: Optional[str], previous_prompt: Prompt, turn: Optional[int]) -> str:
        """
        Generates a prompt using the tree-of-thought strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]): A list of previous prompt entries, each containing a "content" key.
            turn (Optional[int]): The current turn or step in the conversation.

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
