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
        self.purpose: Optional[PromptPurpose] = None

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
        if self.context == PromptContext.DOCUMENTATION:
            tree_of_thoughts_steps = [
                (
                    "Imagine three different OpenAPI specification specialists.\n"
                    "All experts will write down one step of their thinking,\n"
                    "then share it with the group.\n"
                    "After that, all remaining specialists will proceed to the next step, and so on.\n"
                    "If any specialist realizes they're wrong at any point, they will leave.\n"
                    f"The question is: Create an OpenAPI specification for this REST API {self.rest_api} "
                )
            ]
        else:
            tree_of_thoughts_steps = [
                (
                    "Imagine three different Pentest experts are answering this question.\n"
                    "All experts will write down one step of their thinking,\n"
                    "then share it with the group.\n"
                    "After that, all experts will proceed to the next step, and so on.\n"
                    "If any expert realizes they're wrong at any point, they will leave.\n"
                    f"The question is: Create pentests for this REST API {self.rest_api} "
                )
            ]

        # Assuming ChatCompletionMessage and ChatCompletionMessageParam have a 'content' attribute
        previous_content = previous_prompt[turn].content if turn is not None else "initial_prompt"

        self.purpose = PromptPurpose.AUTHENTICATION_AUTHORIZATION

        return "\n".join([previous_content] + tree_of_thoughts_steps)
