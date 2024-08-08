from hackingBuddyGPT.usecases.web_api_testing.prompt_information import PromptStrategy, PromptContext
from hackingBuddyGPT.usecases.web_api_testing.utils.prompts.basic_prompt import BasicPrompt


class TreeOfThoughtPrompt(BasicPrompt):
    def __init__(self, context, prompt_helper):
        super().__init__(context, prompt_helper, PromptStrategy.TREE_OF_THOUGHT)

    def generate_prompt(self, round, hint, previous_prompt):
        tree_of_thoughts_steps = [(
            "Imagine three different experts are answering this question.\n"
            "All experts will write down one step of their thinking,\n"
            "then share it with the group.\n"
            "After that, all experts will proceed to the next step, and so on.\n"
            "If any expert realizes they're wrong at any point, they will leave.\n"
            "The question is: "
        )]
        return "\n".join([previous_prompt[round]["content"]] + tree_of_thoughts_steps)


