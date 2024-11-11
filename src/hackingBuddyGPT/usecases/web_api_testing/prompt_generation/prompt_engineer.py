import ast
import json

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
        schemas: dict = None,
        endpoints: dict = None,
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
        token, description, correct_endpoints = rest_api_info
        self.correct_endpoints = correct_endpoints
        self.token = token
        self.strategy = strategy
        self.open_api_spec = open_api_spec
        self.llm_handler, self.response_handler = handlers
        self.prompt_helper = PromptGenerationHelper(response_handler=self.response_handler,
                                                    schemas=schemas or {},
                                                    endpoints=endpoints,
                                                    description=description)
        self.context = context
        self.turn = 0
        self._prompt_history = history or []
        self.previous_prompt = ""
        self.description = description

        self.strategies = {
            PromptStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper
            ),
            PromptStrategy.TREE_OF_THOUGHT: TreeOfThoughtPrompt(
                context=self.context, prompt_helper=self.prompt_helper
            ),
            PromptStrategy.IN_CONTEXT: InContextLearningPrompt(
                context=self.context,
                prompt_helper=self.prompt_helper,
                context_information={self.turn: {"content": "initial_prompt"}},
                open_api_spec= open_api_spec
            ),
        }

        self.purpose =  PromptPurpose.AUTHENTICATION_AUTHORIZATION

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
        prompt_func = self.strategies.get(self.strategy)
        if prompt_func.strategy == PromptStrategy.IN_CONTEXT:
            prompt_func.open_api_spec = self.open_api_spec
        if not prompt_func:
            raise ValueError("Invalid prompt strategy")

        is_good = False
        self.turn = turn
        prompt = prompt_func.generate_prompt(
                    move_type=move_type, hint=hint, previous_prompt=self._prompt_history, turn=0
                )
        self.purpose = prompt_func.purpose
         #is_good, prompt_history = self.evaluate_response(prompt, log, prompt_history, llm_handler)


        prompt_history.append({"role": "system", "content": prompt})
        self.previous_prompt = prompt
        self.turn += 1
        return prompt_history

    def evaluate_response(self, response, completion, prompt_history, log):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            response (str): The response to evaluate.
            completion (Completion): The completion object with tool call results.
            prompt_history (list): History of prompts and responses.
            log (Log): Logging object for console output.

        Returns:
            tuple: (bool, prompt_history, response, completion) indicating if response is acceptable.
        """
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        if self.token != "":
            response.action.headers =  {
                "Authorization": f"Bearer {self.token}"
                }
        command_str = pydantic_core.to_json(response).decode()
        command = json.loads(command_str)


        log.console.print(Panel(command_str, title="assistant"))

        # Display the command execution status and result
        with log.console.status("[bold green]Executing command..."):
            result = response.execute()
            log.console.print(Panel(result, title="tool"))


        result_str = self.response_handler.parse_http_status_line(result)
        request_path = command.get("action", {}).get("path")

        if "action" not in command:
            return False, prompt_history, response, completion

        # Path evaluation logic
        is_successful = result_str.startswith("200")
        prompt_history.append(message)

        if request_path in self.correct_endpoints:
            if is_successful:
                self.prompt_helper.current_step = 1 if self.prompt_helper.current_step == 3 else self.prompt_helper.current_step + 1
                status_message = f"{request_path} is a correct endpoint"
                self.prompt_helper.found_endpoints.append(request_path)
            else:
                self.prompt_helper.unsuccessful_paths.append(request_path)
                status_message = f"{request_path} is not an endpoint; "


        else:
            if is_successful:
                self.prompt_helper.current_step = 1 if self.prompt_helper.current_step == 3 else self.prompt_helper.current_step + 1
                status_message = f"{request_path} is a correct endpoint"
                self.prompt_helper.found_endpoints.append(request_path)

            else:
                self.prompt_helper.unsuccessful_paths.append(request_path)
                status_message = f"{request_path} is not an endpoint; {request_path}/1 is also incorrect"

        prompt_history.append(tool_message(status_message, tool_call_id))

        return is_successful, prompt_history,  result, result_str

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
