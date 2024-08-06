import abc
import json
import argparse
import typing
from dataclasses import dataclass, field
from rich.panel import Panel
from typing import Dict, Type

from hackingBuddyGPT.utils import LLMResult
from hackingBuddyGPT.utils.configurable import ParameterDefinitions, build_parser, get_arguments, get_class_parameters, \
    Transparent, configurable, Global, ParserState
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.db_storage.db_storage import DbStorage


@dataclass
class Logger:
    log_db: DbStorage
    console: Console
    model: str = ""
    tag: str = ""
    configuration: str = ""

    run_id: int = field(init=False, default=None)

    def __post_init__(self):
        self.run_id = self.log_db.create_new_run(self.model, self.tag, self.configuration)

    def add_log_query(self, turn: int, command: str, result: str, answer: LLMResult):
        self.log_db.add_log_query(self.run_id, turn, command, result, answer)

    def add_log_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: float) -> int:
        return self.log_db.add_log_message(self.run_id, role, content, tokens_query, tokens_response, duration)

    def add_log_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: float):
        self.console.print(f"\n[bold green on gray3]{' ' * self.console.width}\nTOOL RESPONSE:[/bold green on gray3]")
        self.console.print(result_text)
        self.log_db.add_log_tool_call(self.run_id, message_id, tool_call_id, function_name, arguments, result_text, duration)

    def add_log_analyze_response(self, turn: int, command: str, result: str, answer: LLMResult):
        self.log_db.add_log_analyze_response(self.run_id, turn, command, result, answer)

    def add_log_update_state(self, turn: int, command: str, result: str, answer: LLMResult):
        self.log_db.add_log_update_state(self.run_id, turn, command, result, answer)

    def run_was_success(self):
        self.log_db.run_was_success(self.run_id)

    def run_was_failure(self, reason: str):
        self.log_db.run_was_failure(self.run_id, reason)

    def status_message(self, message: str):
        self.log_db.add_log_message(self.run_id, "status", message, 0, 0, 0)


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

    _log: Logger = None

    def init(self, configuration):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        self._log = Logger(self.log_db, self.console, self.get_name(), self.tag, self.serialize_configuration(configuration))

    def serialize_configuration(self, configuration) -> str:
        return json.dumps(configuration)

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

    @abc.abstractmethod
    def perform_round(self, turn: int):
        pass

    def before_run(self):
        pass

    def after_run(self):
        pass

    def run(self):

        self.before_run()

        turn = 1
        try:
            while turn <= self.max_turns and not self._got_root:
                self._log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

                self._got_root = self.perform_round(turn)

                # finish turn and commit logs to storage
                self._log.log_db.commit()
                turn += 1

            self.after_run()

            # write the final result to the database and console
            if self._got_root:
                self._log.run_was_success()
                self._log.console.print(Panel("[bold green]Got Root!", title="Run finished"))
            else:
                self._log.run_was_failure("maximum turn number reached")
                self._log.console.print(Panel("[green]maximum turn number reached", title="Run finished"))

            return self._got_root
        except Exception as e:
            self._log.run_was_failure(f"exception occurred: {e}")
            raise


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
        parser_state = ParserState()
        build_parser(self.parameters, parser, parser_state)
        parser.set_defaults(use_case=self, parser_state=parser_state)

    def __call__(self, args: argparse.Namespace):
        return self.use_case(**get_arguments(self.parameters, args, args.parser_state))


use_cases: Dict[str, _WrappedUseCase] = dict()


T = typing.TypeVar("T")


class AutonomousAgentUseCase(AutonomousUseCase, typing.Generic[T]):
    agent: T = None

    def perform_round(self, turn: int):
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    def get_name(self) -> str:
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    @classmethod
    def __class_getitem__(cls, item):
        item = dataclass(item)
        item.__parameters__ = get_class_parameters(item)

        class AutonomousAgentUseCase(AutonomousUseCase):
            agent: Transparent(item) = None

            def init(self, configuration):
                super().init(configuration)
                self.agent._log = self._log
                self.agent.init()

            def get_name(self) -> str:
                return self.__class__.__name__

            def before_run(self):
                return self.agent.before_run()

            def after_run(self):
                return self.agent.after_run()

            def perform_round(self, turn: int):
                return self.agent.perform_round(turn)

        constructed_class = dataclass(AutonomousAgentUseCase)

        return constructed_class


def use_case(description):
    def inner(cls):
        cls = dataclass(cls)
        name = cls.__name__.removesuffix("UseCase")
        if name in use_cases:
            raise IndexError(f"Use case with name {name} already exists")
        use_cases[name] = _WrappedUseCase(name, description, cls, get_class_parameters(cls))
        return cls
    return inner


def register_use_case(name: str, description: str, use_case: Type[UseCase]):
    """
    This function is used to register a UseCase that was created manually, and not through the use_case decorator.
    """
    if name in use_cases:
        raise IndexError(f"Use case with name {name} already exists")
    use_cases[name] = _WrappedUseCase(name, description, use_case, get_class_parameters(use_case))
