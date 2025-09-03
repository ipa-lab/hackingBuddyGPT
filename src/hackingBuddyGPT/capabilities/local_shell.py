import re
from dataclasses import dataclass
from typing import Tuple

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.utils.connectors.local_shell import LocalShellConnection


@dataclass
class LocalShellCapability(Capability):
    conn: LocalShellConnection

    def describe(self) -> str:
        return "give a command to be executed and I will respond with the terminal output when running this command on the shell via tmux. The given command must not require user interaction. Do not use quotation marks in front and after your command."

    def get_name(self):
        return "local_exec"
    
    def _got_root(self, output: str) -> bool:
        """Check if we got root access based on the command output."""
        if not output.strip():
            return False
        
        lines = output.strip().split('\n')
        last_line = lines[-1] if lines else ''
        
        # Check for common root indicators
        return (
            "root" in output.lower() or 
            last_line.strip().endswith("#") or
            "root@" in last_line or
            last_line.strip() == "#"
        )

    def __call__(self, cmd: str) -> Tuple[str, bool]:
        out, _, _ = self.conn.run(cmd)  # This is CORRECT - use the commented version
        return out, self._got_root(out)