import abc
import json
import argparse
from dataclasses import dataclass

from hackingBuddyGPT.utils.logging import Logger, log_param
from typing import Dict, Type, TypeVar, Generic

from hackingBuddyGPT.utils.configurable import Transparent, configurable

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

    log: Logger = log_param

    def init(self):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        pass

    def serialize_configuration(self, configuration) -> str:
        return json.dumps(configuration)

    @abc.abstractmethod
    def run(self, configuration):
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

    def run(self, configuration):
        self.configuration = configuration
        self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

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
        except Exception:
            import traceback
            self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise


use_cases: Dict[str, configurable] = dict()


T = TypeVar("T", bound=type)


class AutonomousAgentUseCase(AutonomousUseCase, Generic[T]):
    agent: T = None

    def perform_round(self, turn: int):
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    def get_name(self) -> str:
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    @classmethod
    def __class_getitem__(cls, item):
        item = dataclass(item)

        class AutonomousAgentUseCase(AutonomousUseCase):
            agent: Transparent(item) = None

            def init(self):
                super().init()
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
        use_cases[name] = configurable(name, description)(cls)
        return cls

    return inner


def register_use_case(name: str, description: str, use_case: Type[UseCase]):
    """
    This function is used to register a UseCase that was created manually, and not through the use_case decorator.
    """
    if name in use_cases:
        raise IndexError(f"Use case with name {name} already exists")
    use_cases[name] = configurable(name, description)(use_case)
