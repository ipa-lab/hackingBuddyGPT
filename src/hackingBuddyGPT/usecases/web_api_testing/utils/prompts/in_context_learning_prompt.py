from hackingBuddyGPT.usecases.web_api_testing.prompt_information import PromptStrategy, PromptContext
from hackingBuddyGPT.usecases.web_api_testing.utils.prompts.basic_prompt import BasicPrompt


class InContextLearningPrompt(BasicPrompt):
    def __init__(self, context, prompt_helper, prompt):
        super().__init__(context, prompt_helper, PromptStrategy.IN_CONTEXT)
        self.prompt = prompt

    def generate_prompt(self, round, hint, previous_prompt):
        history_content = [entry["content"] for entry in previous_prompt]
        prompt_content = self.prompt.get(round, {}).get("content", "")

        # Add hint if provided
        if hint:
            prompt_content += f"\n{hint}"

        return "\n".join(history_content + [prompt_content])

