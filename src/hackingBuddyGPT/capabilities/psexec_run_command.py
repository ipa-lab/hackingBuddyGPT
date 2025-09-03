from dataclasses import dataclass
from typing import Tuple

from hackingBuddyGPT.utils import PSExecConnection

from ..capability import Capability


@dataclass
class PSExecRunCommand(Capability):
    conn: PSExecConnection

    @property
    def describe(self) -> str:
        return "give a command to be executed on the shell and I will respond with the terminal output when running this command on the windows machine. The given command must not require user interaction. Only state the to be executed command. The command should be used for enumeration or privilege escalation."

    def __call__(self, command: str) -> Tuple[str, bool]:
        return self.conn.run(command)[0], False
