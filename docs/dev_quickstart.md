# Developer Quickstart

So you want to create your own LLM hacking agent? We've got you covered and taken care of the tedious ground work.

Let's start with some basic concepts:

- A (usecase)[docs/use_case.md] is our basic abstraction for an agent. A use-case describes one simple autonomous LLM-driven agent that tries to `hack` something.
- (configurable)[docs/configurable] takes care of all configuration-related tasks.

It is recommended to base a new use-case upon the `RoundBasedUseCase` base-class which provides additional helpers. Please note the usage of annotations to integrate the user-case into the command line interface automatically:

~~~ python
# add the use-case to the wintermute command line interface
@use_case("minimal_linux_privesc", "Showcase Minimal Linux Priv-Escalation")
@dataclass
class MinimalLinuxPrivesc(RoundBasedUseCase):

    # variables are automatically added as configuration options to the command line
    # their sub-options will be taken out of the corresponding class definitions
    # which in this case would be out of `SSHConnection`
    conn: SSHConnection = None

    # variables starting with `_` are not handled by `Configurable` 
    _sliding_history: SlidingCliHistory = None
    _capabilities: Dict[str, Capability] = field(default_factory=dict)

    # use init to perform initialization tasks, d'oh
    def init(self):
        super().init()
        self._sliding_history = SlidingCliHistory(self.llm)

        # capabilities are actions that can be called by the LLM
        self._capabilities["run_command"] = SSHRunCommand(conn=self.conn)
        self._capabilities["test_credential"] = SSHTestCredential(conn=self.conn)
        self._template_size = self.llm.count_tokens(template_next_cmd.source)

    # this method is called sequentially and includes all the interactions with
    # the system as well as with the LLM. If the method returns True, agent
    # execution is stopped. Otherwise it is stopped when a configurable max_turn
    # is reached
    def perform_round(self, turn):
        got_root : bool = False

        with self.console.status("[bold green]Asking LLM for a new command..."):
            # get as much history as fits into the target context size
            history = self._sliding_history.get_history(self.llm.context_size - llm_util.SAFETY_MARGIN - self._template_size)

            # get the next command from the LLM
            answer = self.llm.get_response(template_next_cmd, _capabilities=self._capabilities, history=history, conn=self.conn)
            cmd = llm_util.cmd_output_fixer(answer.result)

        with self.console.status("[bold green]Executing that command..."):
            if answer.result.startswith("test_credential"):
                result, got_root = self._capabilities["test_credential"](cmd)
            else:
                self.console.print(Panel(answer.result, title="[bold cyan]Got command from LLM:"))
                result, got_root = self._capabilities["run_command"](cmd)

        # log and output the command and its result
        self.log_db.add_log_query(self._run_id, turn, cmd, result, answer)
        self._sliding_history.add_command(cmd, result)
        self.console.print(Panel(result, title=f"[bold cyan]{cmd}"))

        # if we got root, we can stop the loop
        return got_root
~~~