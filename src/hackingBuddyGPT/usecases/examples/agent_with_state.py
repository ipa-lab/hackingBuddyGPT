import pathlib
from dataclasses import dataclass
from typing import Any

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.agents import AgentWorldview, TemplatedAgent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import SSHConnection, llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory


@dataclass
class ExPrivEscLinuxTemplatedState(AgentWorldview):
    sliding_history: SlidingCliHistory
    max_history_size: int = 0
    conn: SSHConnection = None

    def __init__(self, conn, llm, max_history_size):
        self.sliding_history = SlidingCliHistory(llm)
        self.max_history_size = max_history_size
        self.conn = conn

    def update(self, capability, cmd: str, result: str):
        self.sliding_history.add_command(cmd, result)

    def to_template(self) -> dict[str, Any]:
        return {"history": self.sliding_history.get_history(self.max_history_size), "conn": self.conn}


class ExPrivEscLinuxTemplated(TemplatedAgent):
    conn: SSHConnection = None

    def init(self):
        super().init()

        # setup default template
        self.set_template(str(pathlib.Path(__file__).parent / "next_cmd.txt"))

        # setup capabilities
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))

        # setup state
        max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self._template_size
        self.set_initial_state(ExPrivEscLinuxTemplatedState(self.conn, self.llm, max_history_size))


@use_case("Showcase Minimal Linux Priv-Escalation")
class ExPrivEscLinuxTemplatedUseCase(AutonomousAgentUseCase[ExPrivEscLinuxTemplated]):
    pass
