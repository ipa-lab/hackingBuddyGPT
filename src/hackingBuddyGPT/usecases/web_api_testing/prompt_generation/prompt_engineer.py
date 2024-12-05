from itertools import cycle

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
    """
               A class responsible for engineering prompts based on different strategies for web API testing.

               Attributes:
                   correct_endpoints (cycle): An infinite cycle iterator over the correct API endpoints.
                   current_endpoint (str): The current endpoint being targeted.
                   token (str): Authentication token for API access.
                   strategy (PromptStrategy): Strategy pattern object determining the type of prompt generation.
                   open_api_spec (dict): Specifications from the OpenAPI documentation used in prompt creation.
                   llm_handler (object): Handles interaction with a language model for generating prompts.
                   response_handler (object): Handles responses from the API or simulation environment.
                   prompt_helper (PromptGenerationHelper): Utility class to assist in prompt generation.
                   context (PromptContext): Information about the current context of prompt generation.
                   turn (int): Counter to track the number of turns or interactions.
                   _prompt_history (list): History of prompts used during the session.
                   previous_prompt (str): The last generated prompt.
                   strategies (dict): A dictionary mapping strategies to their corresponding objects.
                   purpose (PromptPurpose): The purpose or intention behind the current set of prompts.
                   prompt_func (callable): The current function used to generate prompts based on strategy.

               Methods:
                   __init__: Initializes the PromptEngineer with necessary settings and handlers.
                   generate_prompt: Generates a prompt based on the current strategy and updates history.
                   get_purpose: Returns the current purpose of the prompt strategy.
                   process_step: Processes a single step using the current strategy and updates the prompt history.
                   set_pentesting_information: Sets pentesting specific information for prompt modifications.
               """

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
        Initializes the PromptEngineer with specified strategy, history, handlers, and context.

        Args:
            strategy (PromptStrategy): The strategy for prompt generation.
            history (list): A history of previously used prompts.
            handlers (tuple): A tuple containing the language model handler and the response handler.
            context (PromptContext): The current context in which the prompts are being generated.
            open_api_spec (dict): The OpenAPI specifications used for generating prompts.
            prompt_helper (PromptGenerationHelper): A helper utility for generating prompts.
            rest_api_info (tuple): A tuple containing the token, host, correct endpoints, and categorized endpoints information.
        """

        token, host, correct_endpoints, categorized_endpoints = rest_api_info
        self.correct_endpoints = cycle(correct_endpoints)  # Creates an infinite cycle of endpoints
        self.current_endpoint = next(self.correct_endpoints)
        self.token = token
        self.strategy = strategy
        self.open_api_spec = open_api_spec
        self.llm_handler, self.response_handler = handlers
        self.prompt_helper = prompt_helper
        self.prompt_helper.current_test_step = None


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



        self.prompt_func = self.strategies.get(self.strategy)

    def generate_prompt(self, turn: int, move_type="explore", log=None, prompt_history=None, llm_handler=None, hint=""):
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

        if self.context == PromptContext.PENTESTING:
            self.prompt_helper.current_test_step = self.prompt_func.current_step

        if self.purpose == PromptPurpose.LOGGING_MONITORING:
            self.prompt_helper.current_endpoint = next(self.correct_endpoints)

        prompt_history.append({"role": "system", "content": prompt})
        self.previous_prompt = prompt
        self.turn += 1
        return prompt_history

    def get_purpose(self):
        """
        Retrieves the current purpose or objective of the prompt generation strategy.

        Returns:
            PromptPurpose: The purpose associated with the current strategy.
        """
        return self.purpose

    def process_step(self, step: str, prompt_history: list) -> tuple[list, str]:
        """
        Processes a given step by interacting with the language model and updating the history.
f
        Args:
            step (str): The step or command to process.
            prompt_history (list): History of prompts and responses to update.

        Returns:
            tuple: A tuple containing the updated prompt history and the result of processing the step.
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
        """
               Sets pentesting-specific information to adjust the prompt generation accordingly.

               Args:
                   pentesting_information (dict): Information specific to penetration testing scenarios.
        """
        self.pentesting_information = pentesting_information
        self.prompt_func.set_pentesting_information(pentesting_information)
        self.purpose = self.pentesting_information.pentesting_step_list[0]
