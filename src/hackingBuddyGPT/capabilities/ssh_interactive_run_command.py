from dataclasses import dataclass
from typing import override

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection


@dataclass
class SSHInteractiveRunCommand(Capability):
    """Run a command in a persistent interactive SSH shell.

    The marker framing, sudo/su password answering and per-command timeout all live in
    :class:`SSHInteractiveConnection`, so this capability just forwards the command and returns the
    captured output. Because the shell persists, an interactive escalation (``sudo su``) carries
    over into subsequent commands, and the connector records the in-session uid for success checks.
    """

    conn: SSHInteractiveConnection
    timeout: int = 10
    additional_description: str = ""

    @override
    def describe(self) -> str:
        desc = (
            "Give a command to be executed in a Linux shell. The environment is persistent across "
            "commands, so an interactive escalation such as 'sudo su' stays in effect for the "
            "commands that follow."
        )
        if self.conn.banner:
            desc += f"\nThe banner of the machine you're running on is:\n{self.conn.banner}"
        return desc + self.additional_description

    @override
    def get_name(self):
        return "execute_bash_command"

    @override
    async def __call__(self, command: str) -> str:
        if command.startswith(self.get_name()):
            cmd_parts = command.split(" ", 1)
            command = "" if len(cmd_parts) == 1 else cmd_parts[1]

        out, err, _ = await self.conn.run(command, timeout=self.timeout)
        # a command can legitimately produce no output; only fall back to the error text (e.g. a
        # failed connection) when there is genuinely nothing else to report, so failures are visible
        # instead of looking like an empty successful command.
        if not out and err:
            return f"[shell error] {err}"
        return out
