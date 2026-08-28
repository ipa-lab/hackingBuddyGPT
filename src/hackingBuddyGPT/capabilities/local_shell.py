from dataclasses import dataclass
from typing import Tuple

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.utils.connectors.local_shell import LocalShellConnection
from hackingBuddyGPT.utils.shell_root_detection import got_root, is_root_from_id


@dataclass
class LocalShellCapability(Capability):
    conn: LocalShellConnection

    def describe(self) -> str:
        return "give a command to be executed and I will respond with the terminal output when running this command on the shell via tmux. The given command must not require user interaction. Do not use quotation marks in front and after your command."

    def get_name(self):
        return "local_exec"
    
    def _got_root(self, output: str) -> bool:
        """Check if we got root access based on the command output."""
        return is_root_from_id(output) or got_root(self.conn.hostname, output)

    async def __call__(self, cmd: str) -> Tuple[str, bool]:
        out, _, _ = self.conn.run(cmd)  # This is CORRECT - use the commented version
        return out, self._got_root(out)