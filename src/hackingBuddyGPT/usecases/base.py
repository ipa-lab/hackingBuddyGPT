import abc
import json
import argparse
import time
from dataclasses import dataclass, field
from functools import wraps

from rich.console import Group
from rich.panel import Panel
from typing import Dict, Type, Optional, TypeVar, Generic

from hackingBuddyGPT.utils import LLMResult
from hackingBuddyGPT.utils.configurable import ParameterDefinitions, build_parser, get_arguments, get_class_parameters, \
    Transparent, configurable, Global, ParserState
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.db_storage.db_storage import DbStorage


def log_section(name: str, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            with logger.section(name):
                return fun(self, *args, **kwargs)
        return inner
    return outer


def log_conversation(conversation: str, start_section: bool = False, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            with logger.conversation(conversation, start_section):
                return fun(self, *args, **kwargs)
        return inner
    return outer


@configurable("logger", "Logger")
@dataclass
class Logger:
    log_db: DbStorage
    console: Console
    tag: str = ""

    run_id: int = field(init=False, default=None)
    last_order_id: int = 0

    _last_message_id: int = 0
    _current_conversation: Optional[str] = None

    def start_run(self, name: str, configuration: str):
        if self.run_id is not None:
            raise ValueError("Run already started")
        self.run_id = self.log_db.create_new_run(name, self.tag, configuration)

    def add_log_query(self, turn: int, command: str, result: str, answer: LLMResult):
        self.log_db.add_log_query(self.run_id, turn, command, result, answer)

    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    def log_section(self, name: str, from_message: int, to_message: int, duration: float):
        return self.log_db.add_log_section(self.run_id, name, from_message, to_message, duration)

    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    def add_log_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: float) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        self.log_db.add_log_message(self.run_id, message_id, self._current_conversation, role, content, tokens_query, tokens_response, duration)
        self.console.print(Panel(content, title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role)))

        return self._last_message_id

    def add_log_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: float):
        self.console.print(Panel(
            Group(
                Panel(arguments, title="arguments"),
                Panel(result_text, title="result"),
            ),
            title=f"Tool Call: {function_name}"))
        self.log_db.add_log_tool_call(self.run_id, message_id, tool_call_id, function_name, arguments, result_text, duration)

    def run_was_success(self):
        self.status_message("Run finished successfully")
        self.log_db.run_was_success(self.run_id)

    def run_was_failure(self, reason: str):
        self.status_message(f"Run failed: {reason}")
        self.log_db.run_was_failure(self.run_id, reason)

    def status_message(self, message: str):
        self.add_log_message("status", message, 0, 0, 0)

    def system_message(self, message: str):
        self.add_log_message("system", message, 0, 0, 0)

    def call_response(self, llm_result: LLMResult) -> int:
        self.system_message(llm_result.prompt)
        return self.add_log_message("assistant", llm_result.answer, llm_result.tokens_query, llm_result.tokens_response, llm_result.duration)

    def stream_message(self, role: str):
        message_id = self._last_message_id
        self._last_message_id += 1

        return MessageStreamLogger(self, message_id, self._current_conversation, role)


@dataclass
class LogSectionContext:
    logger: Logger
    name: str
    from_message: int

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.monotonic() - self._start
        self.logger.log_section(self.name, self.from_message, self.logger._last_message_id, duration)


@dataclass
class LogConversationContext:
    logger: Logger
    with_section: bool
    conversation: str
    previous_conversation: str

    _section: Optional[LogSectionContext] = None

    def __enter__(self):
        if self.with_section:
            self._section = LogSectionContext(self.logger, self.conversation, self.logger._last_message_id)
            self._section.__enter__()
        self.logger._current_conversation = self.conversation
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._section is not None:
            self._section.__exit__(exc_type, exc_val, exc_tb)
            del self._section
        self.logger._current_conversation = self.previous_conversation


@dataclass
class MessageStreamLogger:
    logger: Logger
    message_id: int
    conversation: str
    role: str

    _completed: bool = False
    _reconstructed_message: str = ""

    def __del__(self):
        if not self._completed:
            print(f"streamed message was not finalized ({self.logger.run_id}, {self.message_id}), please make sure to call finalize() on MessageStreamLogger objects")
            self.finalize(0, 0, 0)

    def append(self, content: str):
        self._reconstructed_message += content
        self.logger.log_db.add_log_message_stream_part(self.logger.run_id, self.message_id, "append", content)

    def finalize(self, tokens_query: int, tokens_response: int, duration, overwrite_finished_message: str = None):
        self._completed = True
        if overwrite_finished_message is not None:
            finished_message = overwrite_finished_message
        else:
            finished_message = self._reconstructed_message

        self.logger.log_db.add_log_message(self.logger.run_id, self.message_id, self.conversation, self.role, finished_message, tokens_query, tokens_response, duration)
        self.logger.log_db.remove_log_message_stream_parts(self.logger.run_id, self.message_id)

        return self.message_id


GlobalLogger = Global(Transparent(Logger))


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

    log: GlobalLogger

    def init(self, configuration):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

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
                with self.log.section(f"round {turn}"):
                    self.log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

                    self._got_root = self.perform_round(turn)

                    turn += 1

            self.after_run()

            # write the final result to the database and console
            if self._got_root:
                self.log.run_was_success()
            else:
                self.log.run_was_failure("maximum turn number reached")

            return self._got_root
        except Exception as e:
            self.log.run_was_failure(f"exception occurred: {e}")
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


T = TypeVar("T")


class AutonomousAgentUseCase(AutonomousUseCase, Generic[T]):
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
