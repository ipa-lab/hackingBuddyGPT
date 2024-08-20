from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptStrategy, PromptContext, \
    PromptPurpose
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

    def __init__(self, context, prompt_helper, rest_api, round):
        """
        Initializes the TreeOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            rest_api (str): The REST API endpoint
            round (int): The round number
        """
        super().__init__(context, prompt_helper, PromptStrategy.TREE_OF_THOUGHT)
        self.rest_api = rest_api
        self.round = round
        self.purpose = None

    def generate_prompt(self, move_type, hint, previous_prompt): # still work in progress
        """
        Generates a prompt using the tree-of-thought strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (str): An optional hint to guide the prompt generation.
            previous_prompt (list): A list of previous prompt entries, each containing a "content" key.

        Returns:
            str: The generated prompt.
        """
        if self.context == PromptContext.DOCUMENTATION:
            tree_of_thoughts_steps = [(
            "Imagine three different OpenAPI specification specialist.\n"
            "All experts will write down one step of their thinking,\n"
            "then share it with the group.\n"
            "After that, all remaining specialists will proceed to the next step, and so on.\n"
            "If any specialist realizes they're wrong at any point, they will leave.\n"
            f"The question is: Create an OpenAPI specification for this REST API {self.rest_api} "
            )]
        else:
            tree_of_thoughts_steps = [(
            "Imagine three different Pentest experts are answering this question.\n"
            "All experts will write down one step of their thinking,\n"
            "then share it with the group.\n"
            "After that, all experts will proceed to the next step, and so on.\n"
            "If any expert realizes they're wrong at any point, they will leave.\n"
            f"The question is: Create pentests for this REST API {self.rest_api} "
            )]
        self.purpose = PromptPurpose.AUTHENTICATION_AUTHORIZATION

        return "\n".join([previous_prompt[self.round]["content"]] + tree_of_thoughts_steps)
