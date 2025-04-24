from instructor.retry import InstructorRetryException

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_generation_helper import (
    PromptGenerationHelper,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.state_learning import (
    InContextLearningPrompt,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.task_planning import (
    ChainOfThoughtPrompt,
    TreeOfThoughtPrompt,
)
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Prompt
from hackingBuddyGPT.utils import tool_message


class PromptEngineer:
    """Prompt engineer that creates prompts of different types."""

    def __init__(
        self,
        strategy: PromptStrategy = None,
        history: Prompt = None,
        handlers=(),
        context: PromptContext = None,
        rest_api: str = "",
        schemas: dict = None,
    ):
        """
        Initializes the PromptEngineer with a specific strategy and handlers for LLM and responses.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            history (dict, optional): The history of chats. Defaults to None.
            handlers (tuple): The LLM handler and response handler.
            context (PromptContext): The context for which prompts are generated.
            rest_api (str, optional): The REST API endpoint.
            schemas (dict, optional): Schemas relevant for the context.
        """
        self.strategy = strategy
        self.rest_api = rest_api
        self.llm_handler, self.response_handler = handlers
        self.prompt_helper = PromptGenerationHelper(response_handler=self.response_handler, schemas=schemas or {})
        self.context = context
        self.turn = 0
        self._prompt_history = history or []

        self.strategies = {
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper
            ),
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper, rest_api=self.rest_api
            ),
            PromptStrategy.IN_CONTEXT: InContextLearningPrompt(
                context=self.context,
                prompt_helper=self.prompt_helper,
                context_information={self.turn: {"content": "initial_prompt"}},
            ),
        }

        self.purpose = None

    def generate_prompt(self, turn: int, move_type="explore", hint=""):
        """
        Generates a prompt based on the specified strategy and gets a response.

        Args:
            turn (int): The current round or step in the process.
            move_type (str, optional): The type of move for the strategy. Defaults to "explore".
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
        self.turn = turn
        while not is_good:
            try:
                prompt = prompt_func.generate_prompt(
                    move_type=move_type, hint=hint, previous_prompt=self._prompt_history, turn=0
                )
                self.purpose = prompt_func.purpose
                is_good = self.evaluate_response(prompt, "")
            except InstructorRetryException:
                hint = f"invalid prompt: {prompt}"

        self._prompt_history.append({"role": "system", "content": prompt})
        self.previous_prompt = prompt
        self.turn += 1
        return self._prompt_history

    def evaluate_response(self, prompt, response_text):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            prompt (str): The generated prompt.
            response_text (str): The response text to evaluate.

        Returns:
            bool: True if the response is acceptable, otherwise False.
        """
        # TODO: Implement a proper evaluation mechanism
        return True

    def get_purpose(self):
        """Returns the purpose of the current prompt strategy."""
        return self.purpose

    def process_step(self, step: str, prompt_history: list) -> tuple[list, str]:
        """
        Helper function to process each analysis step with the LLM.

        Args:
            step (str): The current step to process.
            prompt_history (list): The history of prompts and responses.

        Returns:
            tuple: Updated prompt history and the result of the step processing.
        """
        print(f"Processing step: {step}")
        prompt_history.append({"role": "system", "content": step})

        # Call the LLM and handle the response
        self.prompt_helper.check_prompt(prompt_history, step)
        response, completion = self.llm_handler.call_llm(prompt_history)
        message = completion.choices[0].message
        prompt_history.append(message)
        tool_call_id = message.tool_calls[0].id

        try:
            result = response.execute()
        except Exception as e:
            result = f"Error executing tool call: {str(e)}"
        prompt_history.append(tool_message(str(result), tool_call_id))

        return prompt_history, result
