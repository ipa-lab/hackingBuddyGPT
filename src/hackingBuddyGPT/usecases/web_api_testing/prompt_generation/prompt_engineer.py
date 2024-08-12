from instructor.retry import InstructorRetryException
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.chain_of_thought_prompt import \
    ChainOfThoughtPrompt
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.in_context_learning_prompt import \
    InContextLearningPrompt
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.tree_of_thought_prompt import \
    TreeOfThoughtPrompt


class PromptEngineer:
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, history, handlers, context, rest_api=""):
        """
        Initializes the PromptEngineer with a specific strategy and handlers for LLM and responses.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            history (dict, optional): The history of chats. Defaults to None.
            handlers (tuple): The LLM handler and response handler.
            context (PromptContext): The context for which prompts are generated.
            rest_api (str, optional): The REST API
        """
        self.strategy = strategy
        self.rest_api = rest_api
        self.llm_handler, self.response_handler = handlers
        self.prompt_helper = PromptGenerationHelper(response_handler=self.response_handler)
        self.context = context
        self.round = 0
        self._prompt_history = history or []
        self.previous_prompt = self._prompt_history[self.round]["content"] if self._prompt_history else "initial_prompt"
        self.prompt = {self.round: {"content": "initial_prompt"}}

        self.strategies = {
            PromptStrategy.IN_CONTEXT: InContextLearningPrompt(self.context, self.prompt_helper, self.prompt, self.round).generate_prompt,
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtPrompt(self.context, self.prompt_helper).generate_prompt,
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtPrompt(self.context, self.prompt_helper, self.rest_api, self.round).generate_prompt
        }

    def generate_prompt(self, round,move_type="explore",  hint=""):
        """
        Generates a prompt based on the specified strategy and gets a response.

        Args:
            hint (str, optional): An optional hint to guide the prompt generation. Defaults to "".

        Returns:
            list: Updated prompt history after generating the prompt and receiving a response.

        Raises:
            ValueError: If an invalid prompt strategy is specified.
        """
        prompt_func = self.strategies.get(self.strategy)
        if not prompt_func:
            raise ValueError("Invalid prompt strategy")

        is_good = False
        self.round = round
        while not is_good:
            try:
                if self.context == PromptStrategy.CHAIN_OF_THOUGHT:
                    prompt = prompt_func(move_type, hint, self.previous_prompt)
                else:
                    prompt = prompt_func(move_type, hint, self._prompt_history)
                response_text = self.response_handler.get_response_for_prompt(prompt)
                is_good = self.evaluate_response(prompt, response_text)
            except InstructorRetryException:
                hint = f"invalid prompt: {prompt}"

        self._prompt_history.append({"role": "system", "content": prompt})
        self.previous_prompt = prompt
        self.round += 1
        return self._prompt_history

    def evaluate_response(self, prompt, response_text):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            prompt (str): The generated prompt.
            response_text (str): The response text to evaluate.

        Returns:
            bool: True if the response is acceptable, otherwise False.

        Note:
            The current implementation always returns True. A proper evaluation mechanism should be implemented.
        """
        # TODO: Implement a proper evaluation mechanism
        return True
