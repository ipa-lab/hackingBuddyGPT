from dataclasses import dataclass

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.psexec import PSExecConnection


@dataclass
class PSExecRunCommand(Capability):
    conn: PSExecConnection

    def describe(self) -> str:
        return "give a command to be executed on the shell and I will respond with the terminal output when running this command on the windows machine. The given command must not require user interaction. Only state the to be executed command. The command should be used for enumeration or privilege escalation."

    async def __call__(self, command: str) -> str:
        return self.conn.run(command)[0]
