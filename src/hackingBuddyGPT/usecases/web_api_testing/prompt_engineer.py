
from instructor.retry import InstructorRetryException

from hackingBuddyGPT.usecases.web_api_testing.prompt_information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.utils.prompts.chain_of_thought_prompt import ChainOfThoughtPrompt
from hackingBuddyGPT.usecases.web_api_testing.utils.prompt_helper import PromptHelper
from hackingBuddyGPT.usecases.web_api_testing.utils.prompts.in_context_learning_prompt import InContextLearningPrompt
from hackingBuddyGPT.usecases.web_api_testing.utils.prompts.tree_of_thought_prompt import TreeOfThoughtPrompt


class PromptEngineer(object):
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, history, handlers, context):
        """
        Initializes the PromptEngineer with a specific strategy and handlers for LLM and responses.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            history (dict, optional): The history of chats. Defaults to None.
            handlers (tuple): The LLM handler and response handler
            context (PromptContext): The context for which prompts are generated


        Attributes:
            strategy (PromptStrategy): Stores the provided strategy.
            llm_handler (object): Handles the interaction with the LLM.
            nlp (spacy.lang.en.English): The spaCy English model used for NLP tasks.
            _prompt_history (dict): Keeps track of the conversation history.
            prompt (dict): The current state of the prompt history.
            previous_prompt (str): The previous prompt content based on the conversation history.
            schemas (object): Stores the provided schemas.
            response_handler (object): Manages the response handling logic.
            round (int): Tracks the current round of conversation.
            strategies (dict): Maps strategies to their corresponding methods.
        """
        self.prompt_helper = PromptHelper()
        self.strategy = strategy
        llm_handler , response_handler = handlers
        self.response_handler = response_handler
        self.llm_handler = llm_handler
        self.round = 0
        self._prompt_history = history
        self.prompt = {self.round: {"content": "initial_prompt"}}
        self.previous_prompt = self._prompt_history[self.round]["content"]

        self.context = context

        self.strategies = {
            PromptStrategy.IN_CONTEXT: self.in_context_learning,
            PromptStrategy.CHAIN_OF_THOUGHT: self.chain_of_thought,
            PromptStrategy.TREE_OF_THOUGHT: self.tree_of_thought
        }

    def generate_prompt(self):
        """
        Generates a prompt based on the specified strategy and gets a response.

        This method directly calls the appropriate strategy method to generate
        a prompt and then gets a response using that prompt.
        """
        # Directly call the method using the strategy mapping
        prompt_func = self.strategies.get(self.strategy)
        is_good = False
        if prompt_func:
            while not is_good:
                prompt = prompt_func(self.context)
                try:
                    response_text = self.response_handler.get_response_for_prompt(prompt)
                    is_good = self.evaluate_response(prompt, response_text)
                except InstructorRetryException :
                    prompt = prompt_func(context=self.context, hint=f"invalid prompt:{prompt}")
                if is_good:
                    self._prompt_history.append( {"role":"system", "content":prompt})
                    self.previous_prompt = prompt
                    self.round = self.round +1
                    return self._prompt_history

    def in_context_learning(self, context, hint=""):
        """
        Generates a prompt for in-context learning.

        This method builds a prompt using the conversation history
        and the current prompt.

        Returns:
            str: The generated prompt.
        """
        prompt = InContextLearningPrompt(self.context, prompt_helper=self.prompt_helper, prompt=self.prompt)
        return prompt.generate_prompt(round, hint,self._prompt_history)

    def chain_of_thought(self, context, hint=""):
        """
        Generates a prompt using the chain-of-thought strategy.

        Args:
            context (Context): Determines whether the documentation-oriented chain of thought should be used.
            hint (str): Additional hint to be added to the chain of thought.

        Returns:
            str: The generated prompt.
        """
        prompt = ChainOfThoughtPrompt(self.context, prompt_helper=self.prompt_helper)
        return prompt.generate_prompt(round, hint, self.previous_prompt)

    def tree_of_thought(self, context, hint=""):
        """
        Generates a prompt using the tree-of-thought strategy. https://github.com/dave1010/tree-of-thought-prompting

        This method builds a prompt where multiple experts sequentially reason
        through steps.

        Returns:
            str: The generated prompt.
        """
        prompt = TreeOfThoughtPrompt(self.context, prompt_helper=self.prompt_helper)
        return prompt.generate_prompt(round, hint,self._prompt_history)
    def evaluate_response(self, prompt, response_text): #TODO find a good way of evaluating result of prompt
        return True



