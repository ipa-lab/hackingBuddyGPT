from typing import Dict, Optional

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.state_learning.state_planning_prompt import (
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
    """

    def __init__(self, context: PromptContext, prompt_helper, context_information: Dict[int, Dict[str, str]]) -> None:
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            context_information (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
            round (int): The round number for which the prompt is being generated.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.IN_CONTEXT)
        self.prompt: Dict[int, Dict[str, str]] = context_information
        self.purpose: Optional[PromptPurpose] = None

    def generate_prompt(
        self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Generates a prompt using the in-context learning strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (List[Dict[str, str]]): A list of previous prompt entries, each containing a "content" key.

        Returns:
            str: The generated prompt.
        """
        history_content = [entry["content"] for entry in previous_prompt]
        prompt_content = self.prompt.get(turn, {}).get("content", "")

        # Add hint if provided
        if hint:
            prompt_content += f"\n{hint}"

        return "\n".join(history_content + [prompt_content])
