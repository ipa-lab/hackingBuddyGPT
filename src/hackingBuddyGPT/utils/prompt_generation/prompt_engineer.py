from typing import Any

from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptStrategy, )
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import (
    PromptGenerationHelper,
)
from hackingBuddyGPT.utils.prompt_generation.prompts.state_learning import (
    InContextLearningPrompt,
)
from hackingBuddyGPT.utils.prompt_generation.prompts.task_planning import (
    ChainOfThoughtPrompt,
    TreeOfThoughtPrompt,
)


class PromptEngineer:
    """
        A class responsible for engineering prompts for web API testing based on different strategies.

        Attributes:
            _context (PromptContext): Context of the current prompt generation.
            turn (int): Interaction counter.
            _prompt_helper (PromptGenerationHelper): Helper for managing prompt-related data and logic.
            _prompt_func (callable): Strategy-specific prompt generation function.
            _purpose (PromptPurpose): Current purpose of the prompt strategy.
        """

    def __init__(
            self,
            strategy: PromptStrategy = None,
            context: PromptContext = None,
            open_api_spec: dict = None,
            prompt_helper: PromptGenerationHelper = None,
            rest_api_info: tuple = None,
            prompt_file : Any = None
    ):

        """
        Initialize the PromptEngineer with the given strategy, context, and configuration.

        Args:
            strategy (PromptStrategy): Strategy for prompt generation.
            context (PromptContext): Context for prompt generation.
            open_api_spec (dict): OpenAPI specifications for the API.
            prompt_helper (PromptGenerationHelper): Utility class for prompt generation.
            rest_api_info (tuple): Contains token, host, correct endpoints, and categorized endpoints.
        """

        token, host, correct_endpoints, categorized_endpoints = rest_api_info
        self.host = host
        self._token = token
        self.prompt_helper = prompt_helper
        self.prompt_helper.current_test_step = None
        self.turn = 0
        self._context = context

        strategies = {
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtPrompt(
                context=context, prompt_helper=self.prompt_helper, prompt_file = prompt_file
            ),
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtPrompt(
                context=context, prompt_helper=self.prompt_helper,  prompt_file = prompt_file
            ),
            PromptStrategy.IN_CONTEXT: InContextLearningPrompt(
                context=context,
                prompt_helper=self.prompt_helper,
                context_information={self.turn: {"content": "initial_prompt"}},
                open_api_spec=open_api_spec,
                prompt_file=prompt_file
            ),
        }

        self._prompt_func = strategies.get(strategy)
        if self._prompt_func.strategy == PromptStrategy.IN_CONTEXT:
            self._prompt_func.open_api_spec = open_api_spec

    def generate_prompt(self, turn: int, move_type="explore", prompt_history=None, hint=""):
        """
        Generates a prompt for a given turn and move type, then processes the response.

        Args:
            turn (int): The current interaction number in the sequence.
            move_type (str, optional): The type of interaction, defaults to "explore".
            log (logging.Logger, optional): Logger for debug information, defaults to None.
            prompt_history (list, optional): History of prompts for tracking, defaults to None.
            llm_handler (object, optional): Language model handler if different from initialized, defaults to None.
            hint (str, optional): Optional hint to influence prompt generation, defaults to empty string.

        Returns:
            list: Updated prompt history with the new prompt and response included.

        Raises:
            ValueError: If an invalid prompt strategy is specified.
        """

        if prompt_history is None:
            prompt_history = []
        if not self._prompt_func:
            raise ValueError("Invalid prompt strategy")

        self.turn = turn
        if self.host.__contains__("coincap"):
            hint = "Try as id or other_resoure cryptocurrency names like bitcoin.\n"
        prompt = self._prompt_func.generate_prompt(
            move_type=move_type, hint=hint, previous_prompt=prompt_history, turn=0
        )
        self._purpose = self._prompt_func.purpose

        if self._context == PromptContext.PENTESTING:
            self.prompt_helper.current_test_step = self._prompt_func.current_step
            self.prompt_helper.current_sub_step = self._prompt_func.current_sub_step

        prompt_history.append({"role": "system", "content": prompt})
        self.turn += 1
        return prompt_history

    def set_pentesting_information(self, pentesting_information):
        """
               Sets pentesting-specific information to adjust the prompt generation accordingly.

               Args:
                   pentesting_information (dict): Information specific to penetration testing scenarios.
        """
        self.pentesting_information = pentesting_information
        self._prompt_func.set_pentesting_information(pentesting_information)
        self._purpose = self.pentesting_information.pentesting_step_list[0]
