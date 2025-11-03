import abc
import json
from dataclasses import dataclass

from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.logging import Logger, log_param
from typing import Dict, Type, TypeVar, Generic, override

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

    async def init(self):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        return

    def serialize_configuration(self, configuration) -> str:
        return json.dumps(configuration)

    @abc.abstractmethod
    async def run(self, configuration):
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

    @abc.abstractmethod
    async def perform_round(self, limits: Limits):
        pass

    async def before_run(self, limits: Limits):
        pass

    async def after_run(self):
        pass

    @override
    async def run(self, configuration):
        self.configuration = configuration
        await self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

        limits = Limits(max_rounds=self.max_turns)

        await self.before_run(limits)
        try:
            while not limits.reached():
                async with self.log.section(f"round {limits.rounds}"):
                    # TODO: raw console log
                    self.log.console.log(f"[yellow]Starting turn {limits.rounds} of {limits.max_rounds}")

                    await self.perform_round(limits)
                    limits.register_round()

            await self.after_run()

            if (reason := limits.reason()) is None:
                await self.log.run_was_failure(reason)
            else:
                await self.log.run_was_success()

        except Exception:
            import traceback

            await self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise


use_cases: Dict[str, configurable] = dict()


T = TypeVar("T", bound=type)


class AutonomousAgentUseCase(AutonomousUseCase, Generic[T], abc.ABC):
    agent: T = None

    @override
    async def perform_round(self, limits: Limits):
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    @override
    def get_name(self) -> str:
        raise ValueError("Do not use AutonomousAgentUseCase without supplying an agent type as generic")

    @classmethod
    def __class_getitem__(cls, item: type[AutonomousUseCase]):
        item = dataclass(item)

        class AutonomousAgentUseCase(AutonomousUseCase):
            agent: Transparent(item) = None

            @override
            async def init(self):
                await super().init()
                await self.agent.init()

            @override
            def get_name(self) -> str:
                return self.__class__.__name__

            @override
            async def before_run(self, limits: Limits):
                return await self.agent.before_run(limits)

            @override
            async def after_run(self):
                return await self.agent.after_run()

            @override
            async def perform_round(self, limits: Limits):
                return await self.agent.perform_round(limits)

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
