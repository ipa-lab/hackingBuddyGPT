from typing import Any, Dict, List

from litellm.exceptions import ContextWindowExceededError

from hackingBuddyGPT.capability import capabilities_to_tools, tool_call_to_action

# On a context-window error we retry once with only the most recent messages.
CONTEXT_TRIM_MESSAGES = 10


class LLMHandler:
    """
    Drives the web_api prototypes' interaction with the LLM using litellm tool-calling.

    Each call asks the model to pick exactly one capability (as a tool call) and returns
    ``(response, completion)`` where ``response`` is an executable ``Action`` (``response.action``
    is the chosen capability model, ``response.execute()`` runs it) and ``completion`` is the raw
    litellm response (OpenAI-shaped: ``completion.choices[0].message.tool_calls[0].id`` etc.).
    """

    def __init__(self, llm: Any, capabilities: Dict[str, Any], all_possible_capabilities=None) -> None:
        self.llm = llm
        self._capabilities = capabilities
        self.created_objects: Dict[str, List[Any]] = {}
        self.all_possible_capabilities = all_possible_capabilities

    def get_specific_capability(self, capability_name: str) -> Dict[str, Any]:
        return {capability_name: self.all_possible_capabilities[capability_name]}

    @staticmethod
    def _normalize_messages(prompt: Any) -> List[Dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        if isinstance(prompt, list) and prompt and isinstance(prompt[0], list):
            return prompt[0]
        return prompt

    def _complete(self, messages: List[Dict[str, Any]], capabilities: Dict[str, Any], tool_choice: Any) -> Any:
        tools = capabilities_to_tools(capabilities)
        try:
            completion = self.llm.raw_completion(messages, tools=tools, tool_choice=tool_choice)
        except ContextWindowExceededError:
            # Retry once with only the most recent messages; litellm handles rate-limit retries.
            completion = self.llm.raw_completion(
                messages[-CONTEXT_TRIM_MESSAGES:], tools=tools, tool_choice=tool_choice
            )
        tool_call = completion.choices[0].message.tool_calls[0]
        action = tool_call_to_action(tool_call, capabilities)
        return action, completion

    def execute_prompt(self, prompt: List[Dict[str, Any]]) -> Any:
        """Let the model choose any of the handler's capabilities via a (required) tool call."""
        return self._complete(self._normalize_messages(prompt), self._capabilities, tool_choice="required")

    def execute_prompt_with_specific_capability(self, prompt: List[Dict[str, Any]], capability: Any) -> Any:
        """Force the model to call one specific capability."""
        capabilities = self.get_specific_capability(capability)
        messages = self._normalize_messages(prompt)
        forced = {"type": "function", "function": {"name": capability}}
        try:
            return self._complete(messages, capabilities, tool_choice=forced)
        except Exception:
            # Some providers/models reject a forced function choice; fall back to "required".
            return self._complete(messages, capabilities, tool_choice="required")

    def _add_created_object(self, created_object: Any, object_type: str) -> None:
        """Track created objects by type (capped), used by the OpenAPI documentation handler."""
        if object_type not in self.created_objects:
            self.created_objects[object_type] = []
        if len(self.created_objects[object_type]) < 7:
            self.created_objects[object_type].append(created_object)

    def _get_created_objects(self) -> Dict[str, List[Any]]:
        return self.created_objects
