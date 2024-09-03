from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts import (
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

    def __init__(self, context: PromptContext, prompt_helper, strategy: PromptStrategy):
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
        )
