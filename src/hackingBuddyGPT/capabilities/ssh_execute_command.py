from dataclasses import dataclass
from typing import override

import asyncssh

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.async_ssh_connection import AsyncSSHConnection


@dataclass
class SSHExecuteCommand(Capability):
    """Run a shell command on the (Kali jump-host) target over asyncssh.

    Each command runs in its own channel, so commands issued together in one turn run in parallel and
    no shell state is preserved between commands. The ``mitre_attack_*`` arguments make the model
    classify each action (they are captured in the tool-call log). Ported from cochise's
    ``execute_command``.
    """

    conn: AsyncSSHConnection

    @override
    def describe(self) -> str:
        return (
            "Execute a command in a linux shell on the machine you have access to and return its "
            "output. Each command runs in its own shell, so shell state is NOT preserved between "
            "commands. Commands may run for a while before returning. Do not run interactive or "
            "GUI programs."
        )

    @override
    def get_name(self) -> str:
        return "execute_command"

    @override
    async def __call__(self, command: str, mitre_attack_technique: str, mitre_attack_procedure: str) -> str:
        try:
            return str((await self.conn.run(command))["stdout"])
        except asyncssh.misc.ChannelOpenError:
            # the channel could not be opened (e.g. the shared connection dropped); reconnect and retry once
            await self.conn.connect()
            return str((await self.conn.run(command))["stdout"])
        except asyncssh.process.TimeoutError as e:
            return (
                "Timeout during SSH command execution. The command was stopped; any files it "
                "generated remain on the system. The output so far was:\n\n"
                f"```\n{e.stdout}\n```"
            )
