from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.basic_prompt import BasicPrompt

class TreeOfThoughtPrompt(BasicPrompt):
    """
    A class that generates prompts using the tree-of-thought strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    tree-of-thought strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
    """

    def __init__(self, context, prompt_helper):
        """
        Initializes the TreeOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        """
        super().__init__(context, prompt_helper, PromptStrategy.TREE_OF_THOUGHT)

    def generate_prompt(self, round, hint, previous_prompt):
        """
        Generates a prompt using the tree-of-thought strategy.

        Args:
            round (int): The current round of prompt generation.
            hint (str): An optional hint to guide the prompt generation.
            previous_prompt (list): A list of previous prompt entries, each containing a "content" key.

        Returns:
            str: The generated prompt.
        """
        tree_of_thoughts_steps = [(
            "Imagine three different experts are answering this question.\n"
            "All experts will write down one step of their thinking,\n"
            "then share it with the group.\n"
            "After that, all experts will proceed to the next step, and so on.\n"
            "If any expert realizes they're wrong at any point, they will leave.\n"
            "The question is: "
        )]
        return "\n".join([previous_prompt[round]["content"]] + tree_of_thoughts_steps)
