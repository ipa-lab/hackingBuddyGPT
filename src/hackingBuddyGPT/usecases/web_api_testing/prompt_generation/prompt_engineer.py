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
        self.query_counter = 0
        token, description, correct_endpoints,  categorized_endpoints= rest_api_info
        self.correct_endpoints = correct_endpoints
        self.categorized_endpoints = categorized_endpoints
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

    def extract_json(self, response: str) -> dict:
        try:
            # Find the start of the JSON body by locating the first '{' character
            json_start = response.index('{')
            # Extract the JSON part of the response
            json_data = response[json_start:]
            # Convert the JSON string to a dictionary
            data_dict = json.loads(json_data)
            return data_dict
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Error extracting JSON: {e}")
            return {}

    def evaluate_response(self, response, completion, prompt_history, log):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            response (str): The response to evaluate.
            completion (Completion): The completion object with tool call results.
            prompt_history (list): History of prompts and responses.
            log (Log): Logging object for console output.

        Returns:
            tuple: (bool, prompt_history, result, result_str) indicating if response is acceptable.
        """
        # Extract message and tool call information
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id

        parts = parts = [part for part in response.action.path.split("/") if part]


        if self.prompt_helper.current_step == "instance_level" and len(parts) != 2:
            self.prompt_helper.hint_for_next_round = "Endpoint path has to consist of a resource + / + and id."
            return False, prompt_history, None, None



        # Add Authorization header if token is available
        if self.token:
            response.action.headers = {"Authorization": f"Bearer {self.token}"}

        # Convert response to JSON and display it
        command = json.loads(pydantic_core.to_json(response).decode())
        log.console.print(Panel(json.dumps(command, indent=2), title="assistant"))

        # Execute the command and parse the result
        with log.console.status("[bold green]Executing command..."):
            result = response.execute()
            self.query_counter += 1
            result_dict = self.extract_json(result)
            log.console.print(Panel(result, title="tool"))

        # Parse HTTP status and request path
        result_str = self.response_handler.parse_http_status_line(result)
        request_path = command.get("action", {}).get("path")

        # Check for missing action
        if "action" not in command:
            return False, prompt_history, response, completion

        # Determine if the response is successful
        is_successful = result_str.startswith("200")
        prompt_history.append(message)

        # Determine if the request path is correct and set the status message
        if is_successful:
            # Update current step and add to found endpoints
            self.prompt_helper.found_endpoints.append(request_path)
            status_message = f"{request_path} is a correct endpoint"
        else:
            # Handle unsuccessful paths and error message

            error_msg = result_dict.get("error", {}).get("message", "unknown error")

            if result_str.startswith("400"):
                status_message = f"{request_path} is a correct endpoint, but encountered an error: {error_msg}"

                if error_msg not in self.prompt_helper.correct_endpoint_but_some_error.keys():
                    self.prompt_helper.correct_endpoint_but_some_error[error_msg] = []
                self.prompt_helper.correct_endpoint_but_some_error[error_msg].append(request_path)
                self.prompt_helper.hint_for_next_round = error_msg

            else:
                self.prompt_helper.unsuccessful_paths.append(request_path)
                status_message = f"{request_path} is not a correct endpoint; Reason: {error_msg}"

        if self.query_counter > 50 :
            self.prompt_helper.current_step += 1
            self.prompt_helper.current_category = self.get_next_key(self.prompt_helper.current_category, self.categorized_endpoints)
            self.query_counter = 0

        # Append status message to prompt history
        prompt_history.append(tool_message(status_message, tool_call_id))

        return is_successful, prompt_history, result, result_str

    def get_next_key(self, current_key, dictionary):
        keys = list(dictionary.keys())  # Convert keys to a list
        try:
            current_index = keys.index(current_key)  # Find the index of the current key
            return keys[current_index + 1]  # Return the next key
        except (ValueError, IndexError):
            return None  # Return None if the current key is not found or there is no next key


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
