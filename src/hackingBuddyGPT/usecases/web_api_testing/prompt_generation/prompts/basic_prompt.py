from abc import ABC, abstractmethod
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_information import PromptStrategy

class BasicPrompt(ABC):
    def __init__(self, context, prompt_helper, strategy: PromptStrategy):
        self.strategy = strategy
        self.context = context
        self.prompt_helper = prompt_helper

    @abstractmethod
    def generate_prompt(self, round, hint, previous_prompt):
        pass

