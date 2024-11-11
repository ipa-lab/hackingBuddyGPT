import re
from typing import Any, Dict, List

import openai

from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model


class LLMHandler:
    """
    LLMHandler is a class responsible for managing interactions with a large language model (LLM).
    It handles the execution of prompts and the management of created objects based on the capabilities.

    Attributes:
        llm (Any): The large language model to interact with.
        _capabilities (Dict[str, Any]): A dictionary of capabilities that define the actions the LLM can perform.
        created_objects (Dict[str, List[Any]]): A dictionary to keep track of created objects by their type.
    """

    def __init__(self, llm: Any, capabilities: Dict[str, Any]) -> None:
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

    def call_llm(self, prompt: List[Dict[str, Any]]) -> Any:
        """
        Calls the LLM with the specified prompt and retrieves the response.

        Args:
            prompt (List[Dict[str, Any]]): The prompt messages to send to the LLM.

        Returns:
            Any: The response from the LLM.
        """
        print(f"Initial prompt length: {len(prompt)}")

        def call_model(adjusted_prompt: List[Dict[str, Any]]) -> Any:
            """Helper function to make the API call with the adjusted prompt."""
            print(f'------------------------------------------------')
            print(f'Prompt:{adjusted_prompt[len(adjusted_prompt)-1]}')
            print(f'------------------------------------------------')
            return self.llm.instructor.chat.completions.create_with_completion(
                model=self.llm.model,
                messages=adjusted_prompt,
                response_model=capabilities_to_action_model(self._capabilities),
            )

        # Helper to adjust the prompt based on its length.
        def adjust_prompt_based_on_length(prompt: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            num_prompts = int(len(prompt) - 0.5*len(prompt) if len(prompt) >= 20 else len(prompt) - 0.3*len(prompt))
            return self.adjust_prompt(prompt, num_prompts=num_prompts)

        try:
            # First adjustment attempt based on prompt length
            #adjusted_prompt = adjust_prompt_based_on_length(prompt)
            return call_model(prompt)

        except openai.BadRequestError as e:
            print(f"Error: {str(e)} - Adjusting prompt size and retrying.")

            try:
                # Second adjustment based on token size if the first attempt fails
                adjusted_prompt = adjust_prompt_based_on_length(prompt)
                return call_model(adjusted_prompt)

            except openai.BadRequestError as e:
                print(f"Error: {str(e)} - Further adjusting and retrying.")

                # Final fallback with the smallest prompt size
                shortened_prompt = self.adjust_prompt(prompt, num_prompts=1)
                #print(f"New prompt length: {len(shortened_prompt)}")
                return call_model(shortened_prompt)

    def adjust_prompt(self, prompt: List[Dict[str, Any]], num_prompts: int = 5) -> List[Dict[str, Any]]:
        adjusted_prompt = prompt[len(prompt) - num_prompts - (len(prompt) % 2) : len(prompt)]
        if not isinstance(adjusted_prompt[0], dict):
            adjusted_prompt = prompt[len(prompt) - num_prompts - (len(prompt) % 2) -1 : len(prompt)]
        if adjusted_prompt is None:
            adjusted_prompt = prompt
        if not isinstance(prompt, str):
            adjusted_prompt.reverse()
        last_item = None
        for item in adjusted_prompt:
            if not isinstance(item, dict) and not( isinstance(last_item, dict) and last_item.get("role") == "tool") and last_item != None:
                adjusted_prompt.remove(item)
            last_item = item
        adjusted_prompt.reverse()

        return adjusted_prompt

    def add_created_object(self, created_object: Any, object_type: str) -> None:
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

    def get_created_objects(self) -> Dict[str, List[Any]]:
        """
        Retrieves the dictionary of created objects and prints its contents.

        Returns:
            Dict[str, List[Any]]: The dictionary of created objects.
        """
        print(f"created_objects: {self.created_objects}")
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
                removed_item = removed_item +1
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

        print(f"tokens:{tokens}")
        if removed_item == 0:
            counter = 5
            for item in prompt:
                prompt.remove(item)
                counter = counter +1
        if not isinstance(prompt, str):
            prompt.reverse()
        return prompt

    def get_num_tokens(self, content: str) -> int:
        if not isinstance(content, str):
            content = str(content)
        return len(self._re_word_boundaries.findall(content)) >> 1
