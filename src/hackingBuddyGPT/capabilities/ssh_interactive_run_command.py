import inspect
from dataclasses import dataclass
from typing import override

from hackingBuddyGPT.capabilities._ssh_command import SSHCommandCapability
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection


@dataclass
class SSHInteractiveRunCommand(SSHCommandCapability):
    """Run a command in a persistent interactive SSH shell.

    The marker framing, sudo/su password answering and per-command timeout all live in
    :class:`SSHInteractiveConnection`, so this capability just forwards the command and returns the
    captured output. Because the shell persists, an interactive escalation (``sudo su``) carries
    over into subsequent commands, and the connector records the in-session uid for success checks.
    """

    conn: SSHInteractiveConnection

    _intro = (
        "Give a command to be executed in a Linux shell. The environment is persistent across "
        "commands, so an interactive escalation such as 'sudo su' stays in effect for the "
        "commands that follow."
    )

    @override
    async def __call__(self, command: str) -> str:
        command = self._strip_command_prefix(command)

        result = self.conn.run(command, timeout=self.timeout)
        if inspect.isawaitable(result):
            result = await result
        out, err, _ = result
        # a command can legitimately produce no output; only fall back to the error text (e.g. a
        # failed connection) when there is genuinely nothing else to report, so failures are visible
        # instead of looking like an empty successful command.
        if not out and err:
            return f"[shell error] {err}"
        return out
