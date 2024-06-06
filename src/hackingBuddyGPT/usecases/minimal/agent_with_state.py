
import pathlib
from dataclasses import dataclass

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.utils import SSHConnection, llm_util
from hackingBuddyGPT.usecases.base import use_case
from hackingBuddyGPT.usecases.agents import TemplatedAgent, AgentWorldview
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory

@dataclass
class MinimalLinuxTemplatedPrivescState(AgentWorldview):
    sliding_history: SlidingCliHistory = None
    max_history_size: int = 0

    conn: SSHConnection = None

    def __init__(self, conn, llm, max_history_size):
        self.sliding_history = SlidingCliHistory(llm)
        self.max_history_size = max_history_size
        self.conn = conn

    def update(self, capability, cmd, result):
        self.sliding_history.add_command(cmd, result)

    def to_template(self):
        return {
            'history': self.sliding_history.get_history(self.max_history_size),
            'conn': self.conn
        }

@use_case("minimal_linux_templated_agent", "Showcase Minimal Linux Priv-Escalation")
@dataclass
class MinimalLinuxTemplatedPrivesc(TemplatedAgent):

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
        self.set_initial_state(MinimalLinuxTemplatedPrivescState(self.conn, self.llm, max_history_size))
