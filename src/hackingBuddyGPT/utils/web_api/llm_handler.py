import re
from typing import Any, Dict, List

import openai
from instructor.exceptions import IncompleteOutputException, InstructorRetryException

from hackingBuddyGPT.capability import capabilities_to_action_model


class LLMHandler:
    """
    LLMHandler is a class responsible for managing interactions with a large language model (LLM).
    It handles the execution of prompts and the management of created objects based on the capabilities.

    Attributes:
        llm (Any): The large language model to interact with.
        _capabilities (Dict[str, Any]): A dictionary of capabilities that define the actions the LLM can perform.
        created_objects (Dict[str, List[Any]]): A dictionary to keep track of created objects by their type.
    """

    def __init__(self, llm: Any, capabilities: Dict[str, Any], all_possible_capabilities= None) -> None:
        """
        Initializes the LLMHandler with the specified LLM and capabilities.

        Args:
            llm (Any): The large language model to interact with.
            capabilities (Dict[str, Any]): A dictionary of capabilities that define the actions the LLM can perform.
        """
        self.llm = llm
        self._capabilities = capabilities
        self.created_objects: Dict[str, List[Any]] = {}
        self._re_word_boundaries = re.compile(r"\b")
        self.adjusting_counter = 0
        self.all_possible_capabilities = all_possible_capabilities


    def get_specific_capability(self, capability_name: str) -> Any:
        return {f"{capability_name}": self.all_possible_capabilities[capability_name]}

    def execute_prompt(self, prompt: List[Dict[str, Any]]) -> Any:
        """
        Calls the LLM with the specified prompt and retrieves the response.

        Args:
            prompt (List[Dict[str, Any]]): The prompt messages to send to the LLM.

        Returns:
            Any: The response from the LLM.
        """

        def call_model(prompt: List[Dict[str, Any]]) -> Any:
            """Helper function to make the API call with the adjusted prompt."""
            if isinstance(prompt, list):
                if isinstance(prompt[0], list):
                    adjusted_prompt = prompt[0]
                    prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)

            return self.llm.instructor.chat.completions.create_with_completion(
                model=self.llm.model,
                messages=prompt,
                response_model=capabilities_to_action_model(self._capabilities),
                #max_tokens=200  # adjust as needed
            )

        # Helper to adjust the prompt based on its length.

        try:
            if isinstance(prompt, list) and len(prompt) >= 10:
                adjusted_prompt = prompt[-10:]
                prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)

            if isinstance(prompt, str):
                prompt = [prompt]
            return call_model(prompt)

        except (openai.BadRequestError, IncompleteOutputException, InstructorRetryException) as e:

            try:
                # First adjustment attempt based on prompt length
                self.adjusting_counter = 1
                if isinstance(prompt, list) and len(prompt) >= 5:
                    adjusted_prompt = self.adjust_prompt(prompt, num_prompts=1)
                    adjusted_prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)
                    prompt= adjusted_prompt




                return call_model(prompt)

            except (openai.BadRequestError, IncompleteOutputException, InstructorRetryException) as e:
                # Second adjustment based on token size if the first attempt fails
                adjusted_prompt = self.adjust_prompt(prompt)
                if isinstance(adjusted_prompt, str):
                    adjusted_prompt = [adjusted_prompt]
                if adjusted_prompt == [] or adjusted_prompt == None:
                    adjusted_prompt = prompt[-1:]
                if isinstance(adjusted_prompt, list):
                    if isinstance(adjusted_prompt[0], list):
                        adjusted_prompt = adjusted_prompt[0]
                adjusted_prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)
                self.adjusting_counter = 2
                return call_model(adjusted_prompt)

    def execute_prompt_with_specific_capability(self, prompt: List[Dict[str, Any]], capability: Any) -> Any:
        """
        Calls the LLM with the specified prompt and retrieves the response.

        Args:
            prompt (List[Dict[str, Any]]): The prompt messages to send to the LLM.

        Returns:
            Any: The response from the LLM.
        """

        def call_model(adjusted_prompt: List[Dict[str, Any]], capability: Any) -> Any:
            """Helper function to make the API call with the adjusted prompt."""
            capability = self.get_specific_capability(capability)

            return self.llm.instructor.chat.completions.create_with_completion(
                model=self.llm.model,
                messages=adjusted_prompt,
                response_model=capabilities_to_action_model(capability),
                #max_tokens=1000  # adjust as needed
            )
        try:
            # First adjustment attempt based on prompt length
            if len(prompt) >= 10:
                shortened_prompt = prompt[-10:]
                prompt = self._ensure_that_tool_messages_are_correct(shortened_prompt, prompt)

            return call_model(prompt, capability)

        except (openai.BadRequestError, IncompleteOutputException, InstructorRetryException) as e:

            try:
                # Second adjustment based on token size if the first attempt fails
                adjusted_prompt = self.adjust_prompt(prompt)
                adjusted_prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)

                self.adjusting_counter = 2
                adjusted_prompt =  call_model(adjusted_prompt, capability)
                return adjusted_prompt

            except (openai.BadRequestError, IncompleteOutputException, InstructorRetryException) as e:

                # Final fallback with the smallest prompt size
                shortened_prompt = self.adjust_prompt(prompt)
                shortened_prompt = self._ensure_that_tool_messages_are_correct(shortened_prompt, prompt)
                if isinstance(shortened_prompt, list):
                    if isinstance(shortened_prompt[0], list):
                        shortened_prompt = shortened_prompt[0]
                print(f'shortened_prompt;{shortened_prompt}')
                return call_model(shortened_prompt, capability)

    def adjust_prompt(self, prompt: List[Dict[str, Any]], num_prompts: int = 5) -> List[Dict[str, Any]]:
        """
    Adjusts the prompt list to contain exactly `num_prompts` items.

    Args:
        prompt (List[Dict[str, Any]]): The list of prompts to adjust.
        num_prompts (int): The desired number of prompts. Defaults to 5.

    Returns:
        List[Dict[str, Any]]: The adjusted list containing exactly `num_prompts` items.
    """
        # Ensure the number of prompts does not exceed the total available
        if len(prompt) < num_prompts:
            return prompt  # Return all available if there are fewer prompts than requested

        # Limit to the last `num_prompts` items
        # Ensure not to exceed the available prompts
        adjusted_prompt = prompt[-num_prompts:]
        adjusted_prompt = adjusted_prompt[:len(adjusted_prompt) - len(adjusted_prompt) % 2]


        if adjusted_prompt == []:
            return prompt

        # Ensure adjusted_prompt starts with a dict item

        if not isinstance(adjusted_prompt, str):
            if not isinstance(adjusted_prompt[0], dict):
                adjusted_prompt = prompt[len(prompt) - num_prompts - (len(prompt) % 2) - 1: len(prompt)]

        # If adjusted_prompt is None, fallback to the full prompt
        if not adjusted_prompt:
            adjusted_prompt = prompt

        # Ensure adjusted_prompt items are valid dicts and follow `tool` message constraints
        validated_prompt = self._ensure_that_tool_messages_are_correct(adjusted_prompt, prompt)

        return validated_prompt

    def _ensure_that_tool_messages_are_correct(self, adjusted_prompt, prompt):
        # Ensure adjusted_prompt items are valid dicts and follow `tool` message constraints
        validated_prompt = []
        last_item = None
        if adjusted_prompt[0].get("role") == "tool":
            adjusted_prompt.remove(adjusted_prompt[0])
        adjusted_prompt.reverse()
        # TODO: Fix this logic
        for item in adjusted_prompt:
            if isinstance(item, dict):
                # Remove `tool` messages without a preceding `tool_calls` message
                if item.get("role") == "assistant" and "tool_calls" not in last_item:
                    validated_prompt.remove(last_item)
                    continue


                # Track valid items
                validated_prompt.append(item)
                last_item = item

        # Reverse back if `prompt` is not a string (just in case)
        if not isinstance(validated_prompt, str):
            validated_prompt.reverse()
        if validated_prompt == []:
            validated_prompt = [prompt[-1]]
        if isinstance(validated_prompt, str):
            validated_prompt = [validated_prompt]
        return validated_prompt

    def _add_created_object(self, created_object: Any, object_type: str) -> None:
        """
        Adds a created object to the dictionary of created objects, categorized by object type.

        Args:
            created_object (Any): The object that was created.
            object_type (str): The type/category of the created object.
        """
        if object_type not in self.created_objects:
            self.created_objects[object_type] = []
        if len(self.created_objects[object_type]) < 7:
            self.created_objects[object_type].append(created_object)

    def _get_created_objects(self) -> Dict[str, List[Any]]:
        """
        Retrieves the dictionary of created objects and prints its contents.

        Returns:
            Dict[str, List[Any]]: The dictionary of created objects.
        """
        return self.created_objects

    def adjust_prompt_based_on_token(self, prompt: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(prompt, str):
            prompt.reverse()

        last_item = None
        tokens = 0
        max_tokens = 100
        last_action = ""
        removed_item = 0
        for item in prompt:
            if tokens > max_tokens:
                if not isinstance(last_item, dict):
                    prompt.remove(item)
                else:
                    prompt.remove(item)
                last_action = "remove"
                removed_item = removed_item + 1
            else:

                if last_action == "remove":
                    if isinstance(last_item, dict) and last_item.get('role') == 'tool':
                        prompt.remove(item)
                last_action = ""
                if isinstance(item, dict):
                    new_token_count = tokens + self.get_num_tokens(item["content"])
                    tokens = new_token_count
                else:
                    new_token_count = tokens + 100
                    tokens = new_token_count

            last_item = item

        if removed_item == 0:
            counter = 5
            for item in prompt:
                prompt.remove(item)
                counter = counter + 1
        if not isinstance(prompt, str):
            prompt.reverse()
        return prompt

    def get_num_tokens(self, content: str) -> int:
        if not isinstance(content, str):
            content = str(content)
        return len(self._re_word_boundaries.findall(content)) >> 1
