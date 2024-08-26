from abc import ABC, abstractmethod

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptStrategy, \
    PromptContext


class BasicPrompt(ABC):
    """
    Abstract base class for generating prompts based on different strategies and contexts.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        strategy (PromptStrategy): The strategy used for prompt generation.
    """

    def __init__(self, context, prompt_helper, strategy: PromptStrategy):
        """
        Initializes the BasicPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The strategy used for prompt generation.
        """
        self.context = context
        self.prompt_helper = prompt_helper
        self.strategy = strategy
        if self.context == PromptContext.PENTESTING:
            self.pentesting_information = PenTestingInformation(schemas=prompt_helper.schemas)


    @abstractmethod
    def generate_prompt(self, move_type, hint, previous_prompt):
        """
        Abstract method to generate a prompt.

        This method must be implemented by subclasses.

        Args:
            move_type (str): The type of move to generate.
            hint (str): An optional hint to guide the prompt generation.
            previous_prompt (str): The previous prompt content based on the conversation history.

        Returns:
            str: The generated prompt.
        """
        pass
