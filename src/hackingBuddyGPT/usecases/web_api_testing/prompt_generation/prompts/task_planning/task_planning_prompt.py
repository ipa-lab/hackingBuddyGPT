from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PlanningType,
    PromptContext,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts import (
    BasicPrompt,
)


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

    def __init__(self, context: PromptContext, prompt_helper, strategy: PromptStrategy):
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
        )
