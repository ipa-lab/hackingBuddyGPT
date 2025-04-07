import pathlib

from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.utils.logging import log_conversation
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.utils import SSHConnection, llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent
template_next_cmd = Template(filename=str(template_dir / "next_cmd.txt"))


class ExPrivEscLinux(Agent):
    conn: SSHConnection = None

    _sliding_history: SlidingCliHistory = None
    _max_history_size: int = 0

    def init(self):
        super().init()

        self._sliding_history = SlidingCliHistory(self.llm)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(template_next_cmd.source)

        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))

    @log_conversation("Asking LLM for a new command...")
    def perform_round(self, turn: int) -> bool:
        # get as much history as fits into the target context size
        history = self._sliding_history.get_history(self._max_history_size)

        # get the next command from the LLM
        answer = self.llm.get_response(template_next_cmd, capabilities=self.get_capability_block(), history=history, conn=self.conn)
        message_id = self.log.call_response(answer)

        # clean the command, load and execute it
        capability, cmd, result, got_root = self.run_capability_simple_text(message_id, llm_util.cmd_output_fixer(answer.result))

        # store the results in our local history
        self._sliding_history.add_command(cmd, result)

        # signal if we were successful in our task
        return got_root


@use_case("Showcase Minimal Linux Priv-Escalation")
class ExPrivEscLinuxUseCase(AutonomousAgentUseCase[ExPrivEscLinux]):
    pass
