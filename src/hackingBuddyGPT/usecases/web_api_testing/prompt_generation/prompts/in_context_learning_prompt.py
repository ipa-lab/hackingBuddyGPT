from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.basic_prompt import BasicPrompt

class InContextLearningPrompt(BasicPrompt):
    """
    A class that generates prompts using the in-context learning strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    in-context learning strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        prompt (dict): A dictionary containing the prompts for each round.
    """

    def __init__(self, context, prompt_helper, prompt, round):
        """
        Initializes the InContextLearningPrompt with a specific context, prompt helper, and initial prompt.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            prompt (dict): A dictionary containing the prompts for each round.
            round (int): Number of round.
        """
        super().__init__(context, prompt_helper, PromptStrategy.IN_CONTEXT)
        self.round = round
        self.prompt = prompt

    def generate_prompt(self, move_type, hint, previous_prompt):
        """
        Generates a prompt using the in-context learning strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (str): An optional hint to guide the prompt generation.
            previous_prompt (list): A list of previous prompt entries, each containing a "content" key.

        Returns:
            str: The generated prompt.
        """
        history_content = [entry["content"] for entry in previous_prompt]
        prompt_content = self.prompt.get(self.round, {}).get("content", "")

        # Add hint if provided
        if hint:
            prompt_content += f"\n{hint}"

        return "\n".join(history_content + [prompt_content])
