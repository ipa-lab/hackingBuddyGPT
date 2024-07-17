import abc
import argparse
import typing
from dataclasses import dataclass
from rich.panel import Panel
from typing import Dict, Type

from hackingBuddyGPT.utils.configurable import ParameterDefinitions, build_parser, get_arguments, get_class_parameters, transparent
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.db_storage.db_storage import DbStorage


@dataclass
class Logger:
    log_db: DbStorage
    console: Console
    tag: str = ""
    run_id: int = 0


@dataclass
class UseCase(abc.ABC):
    """
    A UseCase is the combination of tools and capabilities to solve a specific problem.
    It is usually recommended, to have a UseCase be a dataclass, with all the necessary utils (being of type
    @configurable) as fields. Then they can be automatically injected from the command line / environment / .env
    parameters.

    All UseCases should inherit from this class, implement the run method, and be decorated with the @use_case decorator,
    so that they can be automatically discovered and run from the command line.
    """

    log_db: DbStorage
    console: Console
    tag: str = ""

    _run_id: int = 0
    _log: Logger = None

    def init(self):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        self._run_id = self.log_db.create_new_run(self.get_name(), self.tag)
        self._log = Logger(self.log_db, self.console, self.tag, self._run_id)

    @abc.abstractmethod
    def run(self):
        """
        The run method is the main method of the UseCase. It is used to run the UseCase, and should contain the main
        logic. It is recommended to have only the main llm loop in here, and call out to other methods for the
        functionalities of each step.
        """
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        This method should return the name of the use case. It is used for logging and debugging purposes.
        """
        pass


# this runs the main loop for a bounded amount of turns or until root was achieved
@dataclass
class AutonomousUseCase(UseCase, abc.ABC):
    max_turns: int = 10

    _got_root: bool = False


    def setup(self):
        pass

    @abc.abstractmethod
    def perform_round(self, turn: int):
        pass

    def run(self):

        self.setup()

        turn = 1
        while turn <= self.max_turns and not self._got_root:
            self._log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

            self._got_root = self.perform_round(turn)

            # finish turn and commit logs to storage
            self._log.log_db.commit()
            turn += 1

        # write the final result to the database and console
        if self._got_root:
            self._log.log_db.run_was_success(self._run_id, turn)
            self._log.console.print(Panel("[bold green]Got Root!", title="Run finished"))
        else:
            self._log.log_db.run_was_failure(self._run_id, turn)
            self._log.console.print(Panel("[green]maximum turn number reached", title="Run finished"))

        return self._got_root


@dataclass
class _WrappedUseCase:
    """
    A WrappedUseCase should not be used directly and is an internal tool used for initialization and dependency injection
    of the actual UseCases.
    """
    name: str
    description: str
    use_case: Type[UseCase]
    parameters: ParameterDefinitions

    def build_parser(self, parser: argparse.ArgumentParser):
        build_parser(self.parameters, parser)
        parser.set_defaults(use_case=self)

    def __call__(self, args: argparse.Namespace):
        return self.use_case(**get_arguments(self.parameters, args))


use_cases: Dict[str, _WrappedUseCase] = dict()


def use_case(desc: str):
    """
    By wrapping an Agent with this decorator, an AutonomousUseCase will be automatically created to be discoverable and
    can run from the command line.
    """
    if typing.TYPE_CHECKING:
        from hackingBuddyGPT.usecases import Agent
    else:
        Agent = typing.Any

    def inner(cls: Type[Agent]):
        name = cls.__name__
        if name in use_cases:
            raise IndexError(f"Use case with name {name} already exists")
        cls = dataclass(cls)
        cls.__parameters__ = get_class_parameters(cls, name)

        class ConstructedUseCase(AutonomousUseCase):
            agent: transparent(cls) = None

            def init(self):
                super().init()
                self.agent._log = self._log
                self.agent.init()

            def get_name(self) -> str:
                return name
            
            def setup(self):
                self.agent.setup()

            def perform_round(self, turn: int):
                return self.agent.perform_round(turn)

        constructed_class = dataclass(ConstructedUseCase)
        constructed_class.__name__ = name + "UseCase"
        constructed_class.__qualname__ = name + "UseCase"
        constructed_class.__module__ = cls.__module__

        use_cases[name] = _WrappedUseCase(name, desc, constructed_class, get_class_parameters(constructed_class))

        return constructed_class

    return inner
