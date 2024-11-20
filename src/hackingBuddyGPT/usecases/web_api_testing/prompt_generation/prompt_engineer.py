import ast
import json
from itertools import cycle

import pydantic_core
from instructor.retry import InstructorRetryException
from rich.panel import Panel

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptStrategy, PromptPurpose,
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
            open_api_spec: dict = None,
            prompt_helper: PromptGenerationHelper = None,
            rest_api_info: tuple = None,
    ):
        """
        Initializes the PromptEngineer with a specific strategy and handlers for LLM and responses.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            history (dict, optional): The history of chats. Defaults to None.
            handlers (tuple): The LLM handler and response handler.
            context (PromptContext): The context for which prompts are generated.
            open_api_spec (list): OpenAPI spec definitions.
            schemas (dict, optional): Schemas relevant for the context.
            endpoints (dict, optional): Endpoints relevant for the context.
            description (str, optional): The description of the context.
        """
        token, host, correct_endpoints, categorized_endpoints = rest_api_info
        self.correct_endpoints = cycle(correct_endpoints)  # Creates an infinite cycle of endpoints
        self.current_endpoint = next(self.correct_endpoints)
        self.token = token
        self.strategy = strategy
        self.open_api_spec = open_api_spec
        self.llm_handler, self.response_handler = handlers
        self.prompt_helper = prompt_helper

        self.context = context
        self.turn = 0
        self._prompt_history = history or []
        self.previous_prompt = ""

        self.strategies = {
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper,
            ),
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper
            ),
            PromptStrategy.IN_CONTEXT: InContextLearningPrompt(
                context=self.context,
                prompt_helper=self.prompt_helper,
                context_information={self.turn: {"content": "initial_prompt"}},
                open_api_spec=open_api_spec
            ),
        }

        self.purpose = PromptPurpose.AUTHENTICATION

        self.prompt_func = self.strategies.get(self.strategy)

    def generate_prompt(self, turn: int, move_type="explore", log=None, prompt_history=None, llm_handler=None, hint=""):
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
        if self.prompt_func.strategy == PromptStrategy.IN_CONTEXT:
            self.prompt_func.open_api_spec = self.open_api_spec
        if not self.prompt_func:
            raise ValueError("Invalid prompt strategy")

        is_good = False
        self.turn = turn
        prompt = self.prompt_func.generate_prompt(
            move_type=move_type, hint=hint, previous_prompt=self._prompt_history, turn=0
        )
        self.purpose = self.prompt_func.purpose
        # is_good, prompt_history = self.evaluate_response(prompt, log, prompt_history, llm_handler)

        if self.purpose == PromptPurpose.LOGGING_MONITORING:
            self.prompt_helper.current_endpoint = next(self.correct_endpoints)

        prompt_history.append({"role": "system", "content": prompt})
        self.previous_prompt = prompt
        self.turn += 1
        return prompt_history

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
        response, completion = self.llm_handler.execute_prompt(prompt_history)
        message = completion.choices[0].message
        prompt_history.append(message)
        tool_call_id = message.tool_calls[0].id

        try:
            result = response.execute()
        except Exception as e:
            result = f"Error executing tool call: {str(e)}"
        prompt_history.append(tool_message(str(result), tool_call_id))

        return prompt_history, result

    def set_pentesting_information(self, pentesting_information):
        self.pentesting_information = pentesting_information
        self.prompt_func.set_pentesting_information(pentesting_information)
