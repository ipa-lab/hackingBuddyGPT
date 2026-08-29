from dataclasses import dataclass
from typing import override

from hackingBuddyGPT.capability import Capability


@dataclass
class SSHCommandCapability(Capability):
    """Shared skeleton for the single-argument ``execute_bash_command`` SSH shell capabilities.

    Both concrete capabilities share the same fields, the same tool name, the same leading
    tool-name stripping, and the same banner + ``additional_description`` describe tail. They differ
    only in the connector they drive and how they execute the command, so the opening describe
    sentence (``_intro``) and ``__call__`` are supplied by the subclass.
    """

    conn: object
    timeout: int = 10
    additional_description: str = ""

    # opening sentence of describe(); overridden per subclass (plain class attribute, not a field)
    _intro = ""

    @override
    def get_name(self):
        return "execute_bash_command"

    @override
    def describe(self) -> str:
        desc = self._intro
        if self.conn.banner:
            desc += f"\nThe banner of the machine you're running on is:\n{self.conn.banner}"
        return desc + self.additional_description

    def _strip_command_prefix(self, command: str) -> str:
        """Drop a leading ``execute_bash_command`` token the model sometimes prepends to its arg."""
        if command.startswith(self.get_name()):
            cmd_parts = command.split(" ", 1)
            command = "" if len(cmd_parts) == 1 else cmd_parts[1]
        return command
