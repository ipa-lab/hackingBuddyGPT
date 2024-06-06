import abc
import argparse
from dataclasses import dataclass, field
from typing import Dict, Type

from hackingBuddyGPT.utils.configurable import ParameterDefinitions, build_parser, get_arguments, get_class_parameters

class UseCase(abc.ABC):
    """
    A UseCase is the combination of tools and capabilities to solve a specific problem.
    It is usually recommended, to have a UseCase be a dataclass, with all the necessary utils (being of type
    @configurable) as fields. Then they can be automatically injected from the command line / environment / .env
    parameters.

    All UseCases should inherit from this class, implement the run method, and be decorated with the @use_case decorator,
    so that they can be automatically discovered and run from the command line.
    """

    def init(self):
        """
        The init method is called before the run method. It is used to initialize the UseCase, and can be used to
        perform any dynamic setup that is needed before the run method is called. One of the most common use cases is
        setting up the llm capabilities from the tools that were injected.
        """
        pass

    @abc.abstractmethod
    def run(self):
        """
        The run method is the main method of the UseCase. It is used to run the UseCase, and should contain the main
        logic. It is recommended to have only the main llm loop in here, and call out to other methods for the
        functionalities of each step.
        """
        pass


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


def use_case(name: str, desc: str):
    """
    By wrapping a UseCase with this decorator, it will be automatically discoverable and can be run from the command
    line.
    """

    def inner(cls: Type[UseCase]):
        if name in use_cases:
            raise IndexError(f"Use case with name {name} already exists")
        use_cases[name] = _WrappedUseCase(name, desc, cls, get_class_parameters(cls, name))

        return cls

    return inner
