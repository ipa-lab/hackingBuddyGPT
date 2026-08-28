from dataclasses import dataclass
from typing import Tuple

from hackingBuddyGPT.capability import Capability
from hackingBuddyGPT.utils.connectors.local_shell import LocalShellConnection


@dataclass
class LocalShellCapability(Capability):
    conn: LocalShellConnection

    def describe(self) -> str:
        return "give a command to be executed and I will respond with the terminal output when running this command on the shell via tmux. The given command must not require user interaction. Do not use quotation marks in front and after your command."

    def get_name(self):
        return "local_exec"

    async def __call__(self, cmd: str) -> Tuple[str, bool]:
        out, _, _ = self.conn.run(cmd)
        return out, self.conn.root_verified
