import argparse
import dataclasses
import inspect
import os
from dataclasses import dataclass, Field, MISSING, _MISSING_TYPE
from types import NoneType
from typing import Any, Dict, Type, TypeVar, Set, Union, Optional, overload

from dotenv import load_dotenv

load_dotenv()


T = TypeVar("T")


@overload
def parameter(
    *,
    desc: str,
    default: T = ...,
    init: bool = True,
    repr: bool = True,
    hash: Optional[bool] = None,
    compare: bool = True,
    metadata: Optional[Dict[str, Any]] = ...,
    kw_only: Union[bool, _MISSING_TYPE] = MISSING,
) -> T:
    ...

@overload
def parameter(
    *,
    desc: str,
    default: T = ...,
    init: bool = True,
    repr: bool = True,
    hash: Optional[bool] = None,
    compare: bool = True,
    metadata: Optional[Dict[str, Any]] = ...,
    kw_only: Union[bool, _MISSING_TYPE] = MISSING,
) -> Field[T]:
    ...

def parameter(
    *,
    desc: str,
    default: T = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: Optional[bool] = None,
    compare: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    kw_only: Union[bool, _MISSING_TYPE] = MISSING,
) -> Field[T]:
    if metadata is None:
        metadata = dict()
    metadata["desc"] = desc

    return dataclasses.field(
        default=default,
        default_factory=MISSING,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata=metadata,
        kw_only=kw_only,
    )


def get_default(key, default):
    return os.getenv(
        key, os.getenv(key.upper(), os.getenv(key.replace(".", "_"), os.getenv(key.replace(".", "_").upper(), default)))
    )


@dataclass
class ParserState:
    global_parser_definitions: Set[str] = dataclasses.field(default_factory=lambda: set())
    global_configurations: Dict[Type, Dict[str, Any]] = dataclasses.field(default_factory=lambda: dict())


@dataclass
class ParameterDefinition:
    """
    A ParameterDefinition is used for any parameter that is just a simple type, which can be handled by argparse directly.
    """

    name: str
    type: Type
    default: Any
    description: str

    def parser(self, name: str, parser: argparse.ArgumentParser, parser_state: ParserState):
        default = get_default(name, self.default)

        parser.add_argument(
            f"--{name}", type=self.type, default=default, required=default is None, help=self.description
        )

    def get(self, name: str, args: argparse.Namespace, parser_state: ParserState):
        return getattr(args, name)


ParameterDefinitions = Dict[str, ParameterDefinition]


@dataclass
class ComplexParameterDefinition(ParameterDefinition):
    """
    A ComplexParameterDefinition is used for any parameter that is a complex type (which itself only takes simple types,
    or other types that fit the ComplexParameterDefinition), requiring a recursive build_parser.
    It is important to note, that at some point, the parameter must be a simple type, so that argparse (and we) can handle
    it. So if you have recursive type definitions that you try to make configurable, this will not work.
    """

    parameters: ParameterDefinitions
    global_parameter: bool
    transparent: bool = False

    def parser(self, basename: str, parser: argparse.ArgumentParser, parser_state: ParserState):
        if self.global_parameter and self.name in parser_state.global_parser_definitions:
            return

        for name, parameter in self.parameters.items():
            if isinstance(parameter, dict):
                build_parser(parameter, parser, parser_state, next_name(basename, name, parameter))
            else:
                parameter.parser(next_name(basename, name, parameter), parser, parser_state)

        if self.global_parameter:
            parser_state.global_parser_definitions.add(self.name)

    def get(self, name: str, args: argparse.Namespace, parser_state: ParserState):
        def make(name, args):
            args = get_arguments(self.parameters, args, parser_state, name)

            def create():
                instance = self.type(**args)
                if hasattr(instance, "init") and not getattr(self.type, "__transparent__", False):
                    instance.init()
                setattr(instance, "configurable_recreate", create)  # noqa: B010
                return instance

            return create()

        if not self.global_parameter:
            return make(name, args)

        if self.type in parser_state.global_configurations and self.name in parser_state.global_configurations[self.type]:
            return parser_state.global_configurations[self.type][self.name]

        instance = make(name, args)
        if self.type not in parser_state.global_configurations:
            parser_state.global_configurations[self.type] = dict()
        parser_state.global_configurations[self.type][self.name] = instance

        return instance


def get_class_parameters(cls, name: str = None, fields: Dict[str, dataclasses.Field] = None) -> ParameterDefinitions:
    if name is None:
        name = cls.__name__
    if fields is None and hasattr(cls, "__dataclass_fields__"):
        fields = cls.__dataclass_fields__
    return get_parameters(cls.__init__, name, fields)


def get_parameters(fun, basename: str, fields: Dict[str, dataclasses.Field] = None) -> ParameterDefinitions:
    if fields is None:
        fields = dict()

    sig = inspect.signature(fun)
    params: ParameterDefinitions = {}
    for name, param in sig.parameters.items():
        if name == "self" or name.startswith("_"):
            continue

        if not param.annotation:
            raise ValueError(f"Parameter {name} of {basename} must have a type annotation")

        default = param.default if param.default != inspect.Parameter.empty else None
        description = None
        type = param.annotation

        field = None
        if isinstance(default, dataclasses.Field):
            field = default
            default = field.default
        elif name in fields:
            field = fields[name]

        if field is not None:
            description = field.metadata.get("desc", None)
            if field.type is not None:
                type = field.type

        resolution_name = name
        resolution_basename = basename
        if getattr(type, "__global__", False):
            resolution_name = getattr(type, "__global_name__", None)
            if resolution_name is None:
                resolution_name = name
            resolution_basename = resolution_name

        # check if type is an Optional, and then get the actual type
        if hasattr(type, "__origin__") and type.__origin__ is Union and len(type.__args__) == 2 and type.__args__[1] is NoneType:
            type = type.__args__[0]
            default = None

        if hasattr(type, "__parameters__"):
            params[name] = ComplexParameterDefinition(
                resolution_name,
                type,
                default,
                description,
                get_class_parameters(type, resolution_basename),
                global_parameter=getattr(type, "__global__", False),
                transparent=getattr(type, "__transparent__", False),
            )
        elif type in (str, int, float, bool):
            params[name] = ParameterDefinition(resolution_name, type, default, description)
        else:
            raise ValueError(
                f"Parameter {name} of {basename} must have str, int, bool, or a __parameters__ class as type, not {type}"
            )

    return params


def build_parser(parameters: ParameterDefinitions, parser: argparse.ArgumentParser, parser_state: ParserState, basename: str = ""):
    for name, parameter in parameters.items():
        parameter.parser(next_name(basename, name, parameter), parser, parser_state)


def get_arguments(parameters: ParameterDefinitions, args: argparse.Namespace, parser_state: ParserState, basename: str = "") -> Dict[str, Any]:
    return {name: parameter.get(next_name(basename, name, parameter), args, parser_state) for name, parameter in parameters.items()}


Configurable = Type  # TODO: Define type


def configurable(service_name: str, service_desc: str):
    """
    Anything that is decorated with the @configurable decorator gets the parameters of its __init__ method extracted,
    which can then be used with build_parser and get_arguments to recursively prepare the argparse parser and extract the
    initialization parameters. These can then be used to initialize the class with the correct parameters.
    """

    def inner(cls) -> Configurable:
        cls.name = service_name
        cls.description = service_desc
        cls.__service__ = True
        cls.__parameters__ = get_class_parameters(cls)

        return cls

    return inner


def Global(subclass: T, global_name: str = None) -> T:
    class Cloned(subclass):
        __global__ = True
        __global_name__ = global_name
    Cloned.__name__ = subclass.__name__
    Cloned.__qualname__ = subclass.__qualname__
    Cloned.__module__ = subclass.__module__
    return Cloned


def Transparent(subclass: T) -> T:
    """
    setting a type to be transparent means, that it will not increase a level in the configuration tree, so if you have the following classes:

        class Inner:
            a: int
            b: str

            def init(self):
                print("inner init")

        class Outer:
            inner: transparent(Inner)

            def init(self):
                inner.init()

    the configuration will be `--a` and `--b` instead of `--inner.a` and `--inner.b`.

    A transparent attribute will also not have its init function called automatically, so you will need to do that on your own, as seen in the Outer init.
    The function is upper case on purpose, as it is supposed to be used in a Type context
    """

    class Cloned(subclass):
        __transparent__ = True

    Cloned.__name__ = subclass.__name__
    Cloned.__qualname__ = subclass.__qualname__
    Cloned.__module__ = subclass.__module__
    return Cloned


def next_name(basename: str, name: str, param: Any) -> str:
    if isinstance(param, ComplexParameterDefinition) and param.transparent:
        return basename
    elif basename == "":
        return name
    else:
        return f"{basename}.{name}"
