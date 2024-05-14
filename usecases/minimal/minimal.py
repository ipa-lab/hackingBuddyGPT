import pathlib
from dataclasses import dataclass, field

from mako.template import Template
from rich.panel import Panel

from capabilities import SSHRunCommand, SSHTestCredential
from utils import SSHConnection, llm_util
from usecases.base import use_case
from usecases.agents import Agent
from utils.cli_history import SlidingCliHistory

template_dir = pathlib.Path(__file__).parent
template_next_cmd = Template(filename=str(template_dir / "next_cmd.txt"))

@use_case("minimal_linux_privesc", "Showcase Minimal Linux Priv-Escalation")
@dataclass
class MinimalLinuxPrivesc(Agent):

    conn: SSHConnection = None
    
    _sliding_history: SlidingCliHistory = None

    def init(self):
        super().init()
        self._sliding_history = SlidingCliHistory(self.llm)
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))
        self._template_size = self.llm.count_tokens(template_next_cmd.source)

    def perform_round(self, turn):
        got_root : bool = False

        with self.console.status("[bold green]Asking LLM for a new command..."):
            # get as much history as fits into the target context size
            history = self._sliding_history.get_history(self.llm.context_size - llm_util.SAFETY_MARGIN - self._template_size)

            # get the next command from the LLM
            answer = self.llm.get_response(template_next_cmd, capabilities=self.get_capability_block(), history=history, conn=self.conn)
            cmd = llm_util.cmd_output_fixer(answer.result)

        with self.console.status("[bold green]Executing that command..."):
                self.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                result, got_root = self.get_capability(cmd.split(" ", 1)[0])(cmd)

        # log and output the command and its result
        self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)
        self._sliding_history.add_command(cmd, result)
        self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # if we got root, we can stop the loop
        return got_root

@dataclass
class AgentWorldview:
     pass 

class TemplatedAgent(Agent):

    _state: AgentWorldview = None
    _template: Template = None
    _template_size: int = 0

    def init(self):
        super().init()
    
    def set_initial_state(self, initial_state):
        self._state = initial_state

    def set_template(self, template):
        self._template = Template(filename=template)
        self._template_size = self.llm.count_tokens(self._template.source)

    def update_state():
        pass

    def perform_round(self, turn):
        got_root : bool = False

        with self.console.status("[bold green]Asking LLM for a new command..."):
            # TODO output/log state
            options = self._state.to_template()
            options.update({
                'capabilities': self.get_capability_block()
            })

            print(str(options))

            # get the next command from the LLM
            answer = self.llm.get_response(self._template, **options)
            cmd = llm_util.cmd_output_fixer(answer.result)

        with self.console.status("[bold green]Executing that command..."):
                self.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                capability = self.get_capability(cmd.split(" ", 1))
                result, got_root = capability(cmd)

        # log and output the command and its result
        self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)
        self._state = self.update_state(self._state, capability, cmd, result)
        # TODO output/log new state
        self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # if we got root, we can stop the loop
        return got_root

@dataclass
class MinimalLinuxTemplatedPrivescState(AgentWorldview):
    sliding_history: SlidingCliHistory = None
    history: str = ""
    max_history_size: int = 0
    conn: SSHConnection = None

    def __init__(self, conn, llm, max_history_size):
        self.sliding_history = SlidingCliHistory(llm)
        self.max_history_size = max_history_size
        self.conn = conn

    def update(self, capability, cmd, result):
        self.sliding_history.add_command(cmd, result)
        # get as much history as fits into the target context size
        self.history = self.sliding_history.get_history(self.max_history_size)

    def to_template(self):
        return {
            'history': self.history,
            'conn': self.conn
        }

@use_case("privesc_prototype", "Showcase Minimal Linux Priv-Escalation")
@dataclass
class MinimalLinuxTemplatedPrivesc(TemplatedAgent):

    conn: SSHConnection = None
    
    def init(self):
        super().init()

        self.set_template(str(template_dir / "next_cmd.txt"))
        max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self._template_size

        self.set_initial_state(MinimalLinuxTemplatedPrivescState(self.conn, self.llm, max_history_size))

        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))

    # this is called after each command execution and sets the state for the next round
    # input: current state, the executed capability and it's result
    # output: the new state
    def update_state(self, state, capability, cmd, result):
        state.update(capability, cmd, result)