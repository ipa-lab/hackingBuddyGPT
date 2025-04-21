import argparse
import dataclasses
import inspect
import os
import json
from dotenv import dotenv_values
from dataclasses import dataclass, Field, field, MISSING, _MISSING_TYPE
from types import NoneType
from typing import Any, Dict, Type, TypeVar, Set, Union, Optional, overload, Generic, Callable


def repr_text(value: Any, secret: bool = False) -> str:
    if secret:
        return "<secret>"
    if isinstance(value, str):
        return f"'{value}'"
    else:
        return f"{value}"


class no_default:
    pass


class ParameterError(Exception):
    def __init__(self, message: str, name: list[str]):
        super().__init__(message)
        self.name = name


Configurable = Type  # TODO: Define type


C = TypeVar('C', bound=type)


def configurable(name: str, description: str):
    """
    Anything that is decorated with the @configurable decorator gets the parameters of its __init__ method extracted,
    which can then be used with build_parser and get_arguments to recursively prepare the argparse parser and extract the
    initialization parameters. These can then be used to initialize the class with the correct parameters.
    """

    def inner(cls) -> Configurable:
        cls.name = name or cls.__name__
        cls.description = description
        cls._parameter_collection = dict()
        cls._parameter_definition = ComplexParameterDefinition(
            name=[],
            type=cls,
            default=no_default(),
            description=cls.description,
            secret=False,
            parameters={
                name: parameter_definition_for(*metadata, parameter_collection=cls._parameter_collection)
                for name, metadata in get_inspect_parameters_for_class(cls, []).items()
            },
        )

        return cls

    return inner


def Secret(subclass: C) -> C:
    subclass.__secret__ = True
    return subclass


def Global(subclass: C, global_name: Optional[str] = None) -> C:
    subclass.__global__ = True
    subclass.__global_name__ = global_name
    return subclass


def Transparent(subclass: C) -> C:
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

    subclass.__transparent__ = True
    return subclass


def Choice(*subclasses: C, default: Optional[C] =None) -> C:
    class Cloned(subclasses[0]):
        __choice__ = True
        __choices__ = subclasses
        __default__ = default
    Cloned.__name__ = subclasses[0].__name__
    Cloned.__qualname__ = subclasses[0].__qualname__
    Cloned.__module__ = subclasses[0].__module__
    return Cloned


INDENT_WIDTH = 4
INDENT = " " * INDENT_WIDTH

COMMAND_COLOR = "\033[34m"
PARAMETER_COLOR = "\033[32m"
DEFAULT_VALUE_COLOR = "\033[33m"
MUTED_COLOR = "\033[37m"
COLOR_RESET = "\033[0m"


def indent(level: int) -> str:
    return INDENT * level


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
    secret: bool = False,
    global_parameter: bool = False,
    global_name: Optional[str] = None,
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
    metadata["secret"] = secret
    metadata["global"] = global_parameter
    metadata["global_name"] = global_name

    return field(
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


NestedCollection = Union[C, Dict[str, "NestedCollection[C]"]]
ParameterCollection = NestedCollection["ParameterDefinition[C]"]
ParsingResults = NestedCollection[str]
InstanceResults = NestedCollection[Any]


def get_at(collection: NestedCollection[C], name: list[str], at: int = 0, meta: bool = False) -> Optional[C]:
    if len(name) == at:
        if isinstance(collection, dict):
            raise ValueError(f"Value for {'.'.join(name)} not final in collection: {collection}")
        return collection
    if not isinstance(collection, dict):
        raise ValueError(f"Lookup for {'.'.join(name)} overflowing in collection: {collection}")

    cur_name = name[at]
    if len(name) - 1 == at and meta:
        cur_name = "$"+cur_name

    if cur_name not in collection:
        return None

    return get_at(collection[cur_name], name, at + 1, meta)


def set_at(collection: NestedCollection[C], name: list[str], value: C, at: int = 0, meta: bool = False):
    if len(name) == at:
        raise ValueError(f"Lookup for collection {'.'.join(name)} has empty path")

    if not isinstance(collection, dict):
        raise ValueError(f"Lookup for {'.'.join(name)} overflowing in collection: {collection}")

    if len(name) - 1 == at:
        if meta:
            collection["$"+name[at]] = value
        else:
            collection[name[at]] = value
        return

    if name[at] not in collection:
        collection[name[at]] = {}

    return set_at(collection[name[at]], name, value, at + 1, meta)


def dfs_flatmap(collection: NestedCollection[C], func: Callable[[list[str], C], Any], basename: Optional[list[str]] = None):
    if basename is None:
        basename = []
    output = []
    for key, value in collection.items():
        name = basename + [key]
        if isinstance(value, dict):
            output += dfs_flatmap(value, func, name)
        else:
            output.append(func(name, value))
    return output


@dataclass
class ParameterDefinition(Generic[C]):
    """
    A ParameterDefinition is used for any parameter that is just a simple type, which can be handled by argparse directly.
    """

    name: list[str]
    type: C
    default: Any
    description: Optional[str]
    secret: bool

    def __call__(self, collection: ParsingResults, instances: InstanceResults) -> C:
        instance = get_at(instances, self.name)
        if instance is None:
            value = get_at(collection, self.name)
            if value is None:
                raise ParameterError(f"Missing required parameter '--{'.'.join(self.name)}'", self.name)
            instance = self.type(value)
            set_at(instances, self.name, instance)
        return instance

    def get_default(self, defaults: list[tuple[str, ParsingResults]], fail_fast: bool = True) -> tuple[Any, str, str]:
        default_value = None
        default_text = ""
        default_origin = ""
        default_alternatives = False

        defaults = [(source, get_at(values, self.name)) for source, values in defaults]
        defaults.append(("builtin", self.default))
        for source, default in defaults:
            if default is not None and not isinstance(default, no_default):
                if len(default_text) > 0:
                    if not default_alternatives:
                        default_origin += ", alternatives: "
                    else:
                        default_origin += ", "
                    default_origin += f"{repr_text(default, self.secret)} from {source}"
                    default_alternatives = True
                    continue

                default_value = default
                default_origin = f"default from {source}"
                default_text = repr_text(default, self.secret)
                if fail_fast:
                    break

        return default_value, default_text, default_origin

    def to_help(self, defaults: list[tuple[str, ParsingResults]], level: int) -> str:
        eq = ""

        _, default_text, default_origin = self.get_default(defaults, fail_fast=False)
        if len(default_origin) > 0:
            eq = "="
            default_origin = f" ({default_origin})"

        description = self.description or ""
        return f"{indent(level)}{PARAMETER_COLOR}--{'.'.join(self.name)}{COLOR_RESET}{eq}{DEFAULT_VALUE_COLOR}{default_text}{COLOR_RESET}    {description}{MUTED_COLOR}{default_origin}{COLOR_RESET}"


@dataclass
class ComplexParameterDefinition(ParameterDefinition[C]):
    """
    A ComplexParameterDefinition is used for any parameter that is a complex type (which itself only takes simple types,
    or other types that fit the ComplexParameterDefinition), requiring a recursive build_parser.
    It is important to note, that at some point, the parameter must be a simple type, so that argparse (and we) can handle
    it. So if you have recursive type definitions that you try to make configurable, this will not work.
    """

    parameters: dict[str, ParameterDefinition]

    def __call__(self, collection: ParsingResults, instances: InstanceResults):
        # TODO: default handling?
        # we only do instance management on non-top level parameter definitions (those would be the full configurable, which does not need to be cached and also fails)
        instance_name = self.name
        if len(instance_name) == 0:
            instance_name = [f"${self.type.__class__.__name__}"]
        instance = get_at(instances, instance_name, meta=True)
        if instance is None:
            instance = self.type(**{name: param(collection, instances) for name, param in self.parameters.items()})
            if hasattr(instance, "init"):
                if "configuration" in inspect.signature(instance.init).parameters:
                    instance.init(configuration=collection)
                else:
                    instance.init()
            set_at(instances, instance_name, instance, meta=True)
        return instance


def get_inspect_parameters_for_class(cls: type, basename: list[str]) -> dict[str, tuple[inspect.Parameter, list[str], Optional[dataclasses.Field]]]:
    fields = getattr(cls, "__dataclass_fields__", {})
    return {
        name: (param, basename + [name], fields.get(name))
        for name, param in inspect.signature(cls.__init__).parameters.items()
        if not (name == "self" or name.startswith("_") or isinstance(name, NoneType))
    }

def get_type_description_default_for_parameter(parameter: inspect.Parameter, name: list[str], field: Optional[dataclasses.Field] = None) -> tuple[Type, Optional[str], Any]:
    parameter_type: Type = parameter.annotation
    description: Optional[str] = None

    default: Any = parameter.default if parameter.default != inspect.Parameter.empty else no_default()
    if isinstance(default, dataclasses.Field):
        field = default
        default = field.default

    if field is not None:
        description = field.metadata.get("desc", None)
        if field.type is not None:
            if not isinstance(field.type, type):
                raise ValueError(f"Parameter {'.'.join(name)} has an invalid type annotation: {field.type} ({type(field.type)})")
            parameter_type = field.type

    # check if type is an Optional, and then get the actual type
    if hasattr(parameter_type, "__origin__") and parameter_type.__origin__ is Union and len(parameter_type.__args__) == 2 and parameter_type.__args__[1] is NoneType:
        parameter_type = parameter_type.__args__[0]

    return parameter_type, description, default


def parameter_definition_for(param: inspect.Parameter, name: list[str], field: Optional[dataclasses.Field] = None, *, parameter_collection: ParameterCollection) -> ParameterDefinition:
    parameter_type, description, default = get_type_description_default_for_parameter(param, name, field)
    secret_parameter = (field and field.metadata.get("secret", False)) or getattr(parameter_type, "__secret__", False)

    if (field and field.metadata.get("global", False)) or getattr(parameter_type, "__global__", False):
        if field and field.metadata.get("global_name", None):
            name = [field.metadata["global_name"]]
        elif getattr(parameter_type, "__global_name__", None):
            name = [parameter_type["__global_name__"]]
        else:
            name = [name[-1]]

    if (field and field.metadata.get("transparent", False)) or getattr(parameter_type, "__transparent__", False):
        name = name[:-1]

    if parameter_type in (str, int, float, bool):
        existing_parameter = get_at(parameter_collection, name)
        if existing_parameter:
            if existing_parameter.type != parameter_type:
                raise ValueError(f"Parameter {'.'.join(name)} already exists with a different type ({existing_parameter.type} != {parameter_type})")
            if existing_parameter.default != default:
                if existing_parameter.default is None and isinstance(secret_parameter, no_default) \
                    or existing_parameter.default is not None and not isinstance(secret_parameter, no_default):
                        pass  # syncing up "no defaults"
                else:
                    raise ValueError(f"Parameter {'.'.join(name)} already exists with a different default value ({existing_parameter.default} != {default})")
            if existing_parameter.description != description:
                raise ValueError(f"Parameter {'.'.join(name)} already exists with a different description ({existing_parameter.description} != {description})")
            if existing_parameter.secret != secret_parameter:
                raise ValueError(f"Parameter {'.'.join(name)} already exists with a different secret status ({existing_parameter.secret} != {secret_parameter})")
            return existing_parameter
        parameter = ParameterDefinition(name, parameter_type, default, description, secret_parameter)
        set_at(parameter_collection, name, parameter)
    else:
        parameter = ComplexParameterDefinition(
            name=name,
            type=parameter_type,
            default=default,
            description=description,
            secret=secret_parameter,
            parameters={name: parameter_definition_for(*metadata, parameter_collection=parameter_collection) for name, metadata in get_inspect_parameters_for_class(parameter_type, name).items()},
        )

    return parameter




@dataclass
class Parseable(Generic[C]):
    cls: Type[C]
    description: Optional[str]

    _parameter: ComplexParameterDefinition = field(init=False)
    _parameter_collection: ParameterCollection = field(init=False, default_factory=dict)

    def __call__(self, parsing_results: ParsingResults):
        return self._parameter(parsing_results, {})

    def __post_init__(self):
        self._parameter = ComplexParameterDefinition(
            name=[],
            type=self.cls,
            default=no_default(),
            description=self.description,
            secret=False,
            parameters={name: parameter_definition_for(*metadata, parameter_collection=self._parameter_collection) for name, metadata in get_inspect_parameters_for_class(self.cls, []).items()},
        )

    def to_help(self, defaults: list[tuple[str, ParsingResults]], level: int = 0) -> str:
        return "\n".join(dfs_flatmap(self._parameter_collection, lambda _, parameter: parameter.to_help(defaults, level+1)))


CommandMap = dict[str, Union["CommandMap[C]", Parseable[C]]]


def _to_help(name: str, commands: Union[CommandMap[C], Parseable[C]], level: int = 0, max_length: int = 0) -> str:
    h = ""
    if isinstance(commands, Parseable):
        h += f"{indent(level)}{COMMAND_COLOR}{name}{COLOR_RESET}{' ' * (max_length - len(name)+4)} {commands.description}\n"
    elif isinstance(commands, dict):
        h += f"{indent(level)}{COMMAND_COLOR}{name}{COLOR_RESET}:\n"
        max_length = max(max_length, level*INDENT_WIDTH + max(len(k) for k in commands.keys()))
        for name, parser in commands.items():
            h += _to_help(name, parser, level + 1, max_length)
    return h


def to_help_for_commands(program: str, commands: CommandMap[C], command_chain: Optional[list[str]] = None) -> str:
    if command_chain is None:
        command_chain = []
    h = f"usage: {program} {COMMAND_COLOR}{' '.join(command_chain)} <command>{COLOR_RESET} {PARAMETER_COLOR}[--help] [--config config.json] [options...]{COLOR_RESET}\n\n"
    h += _to_help("commands", commands, 0)
    return h


def to_help_for_command(program: str, command: list[str], parseable: Parseable[C], defaults: list[tuple[str, ParsingResults]]) -> str:
    h = f"usage: {program} {COMMAND_COLOR}{' '.join(command)}{COLOR_RESET} {PARAMETER_COLOR}[--help] [--config config.json] [options...]{COLOR_RESET}\n\n"
    h += parseable.to_help(defaults)
    h += "\n"
    return h


class InvalidCommand(ValueError):
    def __init__(self, error: str, command: list[str], usage: str):
        super().__init__(error)
        self.command_list = command
        self.usage = usage


def instantiate(args: list[str], commands: CommandMap[C]) -> tuple[C, ParsingResults]:
    if len(args) == 0:
        raise ValueError("No arguments provided (this is probably a bug in the program)")
    return _instantiate(args[0], args[1:], commands, [])


def _instantiate(program: str, args: list[str], commands: CommandMap[C], command_chain: list[str]) -> tuple[C, ParsingResults]:
    if command_chain is None:
        command_chain = []

    if len(args) == 0:
        raise InvalidCommand("No command provided", command_chain, to_help_for_commands(program, commands))
    if args[0] not in commands:
        raise InvalidCommand(f"Command {args[0]} not found", command_chain, to_help_for_commands(program, commands))

    command = commands[args[0]]
    command_chain.append(args[0])
    if isinstance(command, Parseable):
        return parse_args(program, command_chain, args[1:], command)
    elif isinstance(command, dict):
        try:
            return _instantiate(program, args[1:], command, command_chain)
        except InvalidCommand as e:
            e.command_list.append(args[0])
            raise e
    else:
        raise TypeError(f"Invalid command type {type(command)}")


def get_environment_variables(parsing_results: ParsingResults, parameter_collection: ParameterCollection) -> tuple[str, ParsingResults]:
    env_parsing_results = dict()
    for key, value in os.environ.items():
        # legacy support
        test_key = key.split(".")
        if get_at(parameter_collection, test_key) is None:
            test_key = key.lower().split(".")
            if get_at(parameter_collection, test_key) is None:
                test_key = key.replace("_", ".").split(".")
                if get_at(parameter_collection, test_key) is None:
                    test_key = key.lower().replace("-", ".").split(".")
                    if get_at(parameter_collection, test_key) is None:
                        continue
        set_at(parsing_results, test_key, value)
        set_at(env_parsing_results, test_key, value)
    return ("environment variables", env_parsing_results)


def get_env_file_variables(parsing_results: ParsingResults, parameter_collection: ParameterCollection) -> tuple[str, ParsingResults]:
    env_file_parsing_results = dict()
    for key, value in dotenv_values().items():
        key = key.split(".")
        if get_at(parameter_collection, key) is None:
            continue
        set_at(parsing_results, key, value)
        set_at(env_file_parsing_results, key, value)
    return (".env file", env_file_parsing_results)


def get_config_file_variables(config_file_path: str, parsing_results: ParsingResults, parameter_collection: ParameterCollection) -> tuple[str, ParsingResults]:
    with open(config_file_path, "r") as config_file:
        config_file_parsing_results = json.load(config_file)
    return (f"config file at '{config_file_path}'", config_file_parsing_results)


def filter_secret_values(parsing_results: ParsingResults, parameter_collection: ParameterCollection, basename: Optional[list[str]] = None) -> ParsingResults:
    if basename is None:
        basename = []

    for key, value in parsing_results.items():
        if isinstance(value, dict):
            filter_secret_values(value, parameter_collection, basename + [key])
        else:
            parameter = get_at(parameter_collection, basename + [key])
            if parameter.secret:
                parsing_results[key] = "<secret>"


def parse_args(program: str, command: list[str], direct_args: list[str], parseable: Parseable[C], parse_env_file: bool = True, parse_environment: bool = True) -> tuple[C, ParsingResults]:
    parameter_collection = parseable._parameter_collection

    parsing_results: ParsingResults = dict()
    defaults: list[tuple[str, ParsingResults]] = []
    if parse_environment:
        defaults.append(get_environment_variables(parsing_results, parameter_collection))

    if parse_env_file:
        defaults.append(get_env_file_variables(parsing_results, parameter_collection))

    if "--config" in direct_args:
        config_file_idx = direct_args.index("--config")
        direct_args.pop(config_file_idx)

        if len(direct_args) < config_file_idx + 1:
            raise ValueError("Missing config file argument")

        config_file_name = direct_args.pop(config_file_idx)
        defaults.append(get_config_file_variables(config_file_name, parsing_results, parameter_collection))

    def _help():
        return to_help_for_command(program, command, parseable, defaults)

    if any(arg in ("--help", "-h") for arg in direct_args):
        raise InvalidCommand("", command, _help())

    while len(direct_args) > 0:
        arg = direct_args.pop(0)
        if arg.startswith("--"):
            key = arg[2:]
            if "=" in key:
                key, value = key.split("=", 1)
            else:
                if len(direct_args) == 0:
                    raise InvalidCommand(f"No value for argument {arg}", command, _help())
                value = direct_args.pop(0)
            key = key.split(".")
            if get_at(parameter_collection, key) is None:
                raise InvalidCommand(f"Invalid argument {arg}", command, _help())
            set_at(parsing_results, key, value)
        else:
            raise InvalidCommand(f"Invalid argument {arg}", command, _help())

    def populate_default(name: list[str], parameter: ParameterDefinition):
        if get_at(parsing_results, name) is None:
            default, _, _ = parameter.get_default(defaults)
            set_at(parsing_results, name, default)

    dfs_flatmap(parameter_collection, populate_default)

    try:
        instance = parseable(parsing_results)
    except ParameterError as e:
        raise InvalidCommand(f"{e}", command, _help()) from e

    filter_secret_values(parsing_results, parameter_collection)
    return instance, parsing_results
