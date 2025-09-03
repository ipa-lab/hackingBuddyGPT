import datetime
from typing import Dict
from hackingBuddyGPT.utils.logging import Logger

from hackingBuddyGPT.capability import (
    Capability,
    capabilities_to_simple_text_handler,
)

class CapabilityManager:
    log: Logger = None

    _capabilities: Dict[str, Capability] = {}
    _default_capability: Capability = None

    def __init__(self, log):
        self.log = log

    def add_capability(self, cap: Capability, name: str = None, default: bool = False):
        if name is None:
            name = cap.get_name()
        self._capabilities[name] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name: str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

    def run_capability_json(self, message_id: int, tool_call_id: str, capability_name: str, arguments: str) -> str:
        capability = self.get_capability(capability_name)

        tic = datetime.datetime.now()
        try:
            result = capability.to_model().model_validate_json(arguments).execute()
        except Exception as e:
            result = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        self.log.add_tool_call(message_id, tool_call_id, capability_name, arguments, result, duration)
        return result

    def run_capability_simple_text(self, message_id: int, cmd: str) -> tuple[str, str, str, bool]:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities, default_capability=self._default_capability)

        tic = datetime.datetime.now()
        try:
            success, output = parser(cmd)
        except Exception as e:
            success = False
            output = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        if not success:
            self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return "", "", output, False

        capability, cmd, (result, got_root) = output
        self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return capability, cmd, result, got_root

    def get_capability_block(self) -> str:
        capability_descriptions, _parser = capabilities_to_simple_text_handler(self._capabilities)
        return "You can either\n\n" + "\n".join(f"- {description}" for description in capability_descriptions.values())

