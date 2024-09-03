from abc import ABC, abstractmethod
from typing import Optional

# from hackingBuddyGPT.usecases.web_api_testing.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import (
    PenTestingInformation,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy,
)


class BasicPrompt(ABC):
    """
    Abstract base class for generating prompts based on different strategies and contexts.

    This class serves as a blueprint for creating specific prompt generators that operate under different strategies,
    such as chain-of-thought or simple prompt generation strategies, tailored to different contexts like documentation
    or pentesting.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        strategy (PromptStrategy): The strategy used for prompt generation.
        pentesting_information (Optional[PenTestingInformation]): Contains information relevant to pentesting when the context is pentesting.
    """

    def __init__(
        self,
        context: PromptContext = None,
        planning_type: PlanningType = None,
        prompt_helper=None,
        strategy: PromptStrategy = None,
    ):
        """
        Initializes the BasicPrompt with a specific context, prompt helper, and strategy.

        Args:
            context (PromptContext): The context in which prompts are generated.
            planning_type (PlanningType): The type of planning.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            strategy (PromptStrategy): The strategy used for prompt generation.
        """
        self.context = context
        self.planning_type = planning_type
        self.prompt_helper = prompt_helper
        self.strategy = strategy
        self.pentesting_information: Optional[PenTestingInformation] = None

        if self.context == PromptContext.PENTESTING:
            self.pentesting_information = PenTestingInformation(schemas=prompt_helper.schemas)

    @abstractmethod
    def generate_prompt(
        self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Abstract method to generate a prompt.

        This method must be implemented by subclasses to generate a prompt based on the given move type, optional hint, and previous prompt.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (Optional[str]): The previous prompt content based on the conversation history.
            turn (Optional[int]): The current turn

        Returns:
            str: The generated prompt.
        """
        pass
