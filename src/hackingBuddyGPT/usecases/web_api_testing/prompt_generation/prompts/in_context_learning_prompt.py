from typing import List, Dict, Optional

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptStrategy, \
    PromptContext, PromptPurpose
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.basic_prompt import BasicPrompt
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.utils import PromptGenerationHelper


class InContextLearningPrompt(BasicPrompt):
    """
    A class that generates prompts using the in-context learning strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    in-context learning strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        prompt (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
        round (int): The round number for which the prompt is being generated.
        purpose (Optional[PromptPurpose]): The purpose of the prompt generation, which can be set during the process.
    """

    def __init__(self, context: PromptContext, prompt_helper: PromptGenerationHelper, prompt: Dict[int, Dict[str, str]], round: int) -> None:
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            prompt (Dict[int, Dict[str, str]]): A dictionary containing the prompts for each round.
            round (int): The round number for which the prompt is being generated.
        """
        super().__init__(context, prompt_helper, PromptStrategy.IN_CONTEXT)
        self.round: int = round
        self.prompt: Dict[int, Dict[str, str]] = prompt
        self.purpose: Optional[PromptPurpose] = None

    def generate_prompt(self, move_type: str, hint: Optional[str], previous_prompt: List[Dict[str, str]]) -> str:
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
        prompt_content = self.prompt.get(self.round, {}).get("content", "")

        # Add hint if provided
        if hint:
            prompt_content += f"\n{hint}"

        return "\n".join(history_content + [prompt_content])
