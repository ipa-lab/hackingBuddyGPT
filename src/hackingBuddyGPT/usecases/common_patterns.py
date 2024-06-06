import abc

from dataclasses import dataclass
from rich.panel import Panel

from .base import UseCase
from hackingBuddyGPT.utils import Console, DbStorage
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection

# this set ups all the console and database stuff, and runs the main loop for a bounded amount of turns
@dataclass
class RoundBasedUseCase(UseCase, abc.ABC):
    log_db: DbStorage
    console: Console
    llm: OpenAIConnection = None
    tag: str = ""
    max_turns: int =10

    _got_root: bool = False
    _run_id: int = 0

    def init(self):
        super().init()
        self._run_id = self.log_db.create_new_run(self.llm.model, self.llm.context_size, self.tag)

    # callback
    def setup(self):
        pass

    # callback
    @abc.abstractmethod
    def perform_round(self, turn: int):
        pass

    # callback
    def teardown(self):
        pass

    def run(self):

        self.setup()

        turn = 1
        while turn <= self.max_turns and not self._got_root:
            self.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

            self._got_root = self.perform_round(turn)

            # finish turn and commit logs to storage
            self.log_db.commit()
            turn += 1
        
        # write the final result to the database and console
        if self._got_root:
            self.log_db.run_was_success(self._run_id, turn)
            self.console.print(Panel("[bold green]Got Root!", title="Run finished"))
        else:
            self.log_db.run_was_failure(self._run_id, turn)
            self.console.print(Panel("[green]maximum turn number reached", title="Run finished"))

        self.teardown()
        return self._got_root