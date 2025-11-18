import abc
import copy
from functools import partial, wraps
import inspect
from typing import Any, Callable, Dict, Iterable, TypeVar, ParamSpec, Type, Union, Awaitable, override

import openai
from openai.types.chat import ChatCompletionToolParam
from openai.types.chat.completion_create_params import Function
from pydantic import BaseModel, create_model
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue


P = ParamSpec("P")
R = TypeVar("R")


def awaitable(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)

    return wrapper


class Capability(abc.ABC):
    """
    A capability is something that can be used by an LLM to perform a task.
    The method signature for the __call__ method is not yet defined, but it will probably be different for different
    types of capabilities (though it is recommended to have the same signature for capabilities, that accomplish the
    same task but slightly different / for a different target).

    At the moment, this is not yet a very powerful class, but in the near-term future, this will provide an automated
    way of providing a json schema for the capabilities, which can then be used for function-calling LLMs.
    """

    @abc.abstractmethod
    def describe(self) -> str:
        """
        describe should return a string that describes the capability. This is used to generate the help text for the
        LLM.

        This is a method and not just a simple property on purpose (though it could become a @property in the future, if
        we don't need the name parameter anymore), so that it can template in some of the capabilities parameters into
        the description.
        """
        pass

    def get_name(self) -> str:
        return type(self).__name__

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs) -> str:
        """
        The actual execution of a capability, please make sure, that the parameters and return type of your
        implementation are well typed, as this is used to properly support function calling.
        """
        pass

    def to_model(self) -> type[BaseModel]:
        """
        Converts the parameters of the `__call__` function of the capability to a pydantic model, that can be used to
        interface with an LLM using eg the openAI function calling API.
        The model will have the same name as the capability class and will have the same fields as the `__call__`,
        the `__call__` method can then be accessed by calling the `execute` method of the model.
        """
        sig = inspect.signature(self.__call__)
        fields = {
            param: (
                param_info.annotation,
                param_info.default if param_info.default is not inspect._empty else ...,
            )
            for param, param_info in sig.parameters.items()
        }
        model_type = create_model(self.__class__.__name__, __doc__=self.describe(), **fields)

        async def execute(model):
            return await self(**model.dict())

        model_type.execute = execute

        return model_type


# An Action is the base class to allow proper typing information of the generated class in `capabilities_to_action_mode`
# This description should not be moved into a docstring inside the class, as it will otherwise be provided in the LLM prompt
class Action(BaseModel):
    action: BaseModel

    async def execute(self):
        return await self.action.execute()


class OptimizedSchemaGenerator(GenerateJsonSchema):
    def generate(
        self,
        schema: Any,
        mode: str = "validation",
    ) -> JsonSchemaValue:
        data = super().generate(schema, mode=mode)
        self._strip_private_fields(data)
        defs = data.get("$defs")
        if defs:
            self._inline_refs(data, defs, seen=set())
            # if you want *all* refs inlined, you can safely drop $defs now
            data.pop("$defs", None)
        return data

    def _strip_private_fields(self, schema: Any) -> None:
        if isinstance(schema, dict):
            # Drop properties starting with "_"
            props = schema.get("properties")
            if isinstance(props, dict):
                for name in list(props.keys()):
                    if name.startswith("_"):
                        del props[name]

            # Recurse into nested dicts/lists
            for v in schema.values():
                self._strip_private_fields(v)

        elif isinstance(schema, list):
            for item in schema:
                self._strip_private_fields(item)

    def _inline_refs(self, node: Any, defs: dict[str, Any], seen: set[str]) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                key = ref.split("/")[-1]
                target = defs.get(key)
                if target is not None:
                    # naive cycle guard: if we’ve already inlined this key on the path, bail
                    if key in seen:
                        return  # leave the $ref to avoid infinite recursion
                    new_seen = set(seen)
                    new_seen.add(key)

                    inlined = copy.deepcopy(target)
                    self._inline_refs(inlined, defs, new_seen)

                    node.clear()
                    node.update(inlined)
                return  # important: don't also walk children of this dict-as-it-was

            # no direct $ref: recurse into children
            for v in list(node.values()):
                self._inline_refs(v, defs, seen)

        elif isinstance(node, list):
            for item in node:
                self._inline_refs(item, defs, seen)


def capability_list_to_dict(capabilities: list[Capability]) -> dict[str, Capability]:
    duplicates: list[str] = []
    result: dict[str, Capability] = {}
    for capability in capabilities:
        capability_name = capability.get_name()
        if capability_name in result:
            duplicates.append(capability_name)
        else:
            result[capability_name] = capability
    if duplicates:
        raise ValueError(f"Duplicate capabilities: {', '.join(duplicates)}")
    return result


def capabilities_to_action_model(capabilities: dict[str, Capability]) -> type[Action]:
    """
    When one of multiple capabilities should be used, then an action model can be created with this function.
    This action model is a pydantic model, where all possible capabilities are represented by their respective models in
    a union type for the action field.
    This allows the LLM to define an action to be used, which can then simply be called using the `execute` function on
    the model returned from here.
    """

    class Model(Action):
        action: Union[tuple([capability.to_model() for capability in capabilities.values()])]

    return Model


SimpleTextHandlerResult = tuple[bool, Union[str, tuple[str, str, ...]]]
SimpleTextHandler = Callable[[str], SimpleTextHandlerResult]


def capabilities_to_simple_text_handler(
    capabilities: Dict[str, Capability],
    default_capability: Capability = None,
    include_description: bool = True,
) -> tuple[Dict[str, str], SimpleTextHandler]:
    """
    This function generates a simple text handler from a set of capabilities.
    It is to be used when no function calling is available, and structured output is not to be trusted, which is why it
    only supports the most basic of parameter types for the capabilities (str, int, float, bool).

    As result it returns a dictionary of capability names to their descriptions and a parser function that can be used
    to parse the text input and execute it. The first return value of the parser function is a boolean indicating
    whether the parsing was successful, the second return value is a tuple containing the capability name, the parameters
    as a string and the result of the capability execution.
    """

    def get_simple_fields(func, name) -> Dict[str, Type]:
        sig = inspect.signature(func)
        fields = {param: param_info.annotation for param, param_info in sig.parameters.items()}
        for param, param_type in fields.items():
            if param_type not in (str, int, float, bool):
                raise ValueError(
                    f"The command {name} is not compatible with this calling convention (this is not a LLM error,"
                    f"but rather a problem with the capability itself, the parameter {param} is {param_type} and not a simple type (str, int, float, bool))"
                )
        return fields

    def parse_params(fields, params) -> tuple[bool, Union[str, Dict[str, Any]]]:
        split_params = params.split(" ", maxsplit=len(fields) - 1)
        if len(split_params) != len(fields):
            return False, "Invalid number of parameters"

        parsed_params = dict()
        for param, param_type in fields.items():
            try:
                parsed_params[param] = param_type(split_params.pop(0))
            except ValueError as e:
                return False, f"Could not parse parameter {param}: {e}"
        return True, parsed_params

    capability_descriptions = dict()
    capability_params = dict()
    for capability_name, capability in capabilities.items():
        fields = get_simple_fields(capability.__call__, capability_name)

        description = f"`{capability_name}"
        if len(fields) > 0:
            description += " " + " ".join(param for param in fields)
        description += "`"
        if include_description:
            description += f": {capability.describe()}"

        capability_descriptions[capability_name] = description
        capability_params[capability_name] = fields

    def parser(text: str) -> SimpleTextHandlerResult:
        capability_name_and_params = text.split(" ", maxsplit=1)
        if len(capability_name_and_params) == 1:
            capability_name = capability_name_and_params[0]
            params = ""
        else:
            capability_name, params = capability_name_and_params
        if capability_name not in capabilities:
            return False, "Unknown command"

        success, parsing_result = parse_params(capability_params[capability_name], params)
        if not success:
            return False, parsing_result

        return True, (capability_name, params, capabilities[capability_name](**parsing_result))

    resolved_parser: SimpleTextHandler = parser

    if default_capability is not None:
        default_fields = get_simple_fields(default_capability.__call__, "__default__")

        def default_capability_parser(text: str) -> SimpleTextHandlerResult:
            success, *output = parser(text)
            if success:
                return success, *output

            params = text
            success, parsing_result = parse_params(default_fields, params)
            if not success:
                params = text.split(" ", maxsplit=1)[1]
                success, parsing_result = parse_params(default_fields, params)
                if not success:
                    return False, parsing_result

            return True, (capability_name, params, default_capability(**parsing_result))

        resolved_parser = default_capability_parser

    return capability_descriptions, resolved_parser


def capabilities_to_functions(
    capabilities: Dict[str, Capability],
) -> Iterable[openai.types.chat.completion_create_params.Function]:
    """
    This function takes a dictionary of capabilities and returns a dictionary of functions, that can be called with the
    parameters of the respective capabilities.
    """
    return [
        Function(
            name=name,
            description=capability.describe(),
            parameters=capability.to_model().model_json_schema(schema_generator=OptimizedSchemaGenerator),
        )
        for name, capability in capabilities.items()
    ]


def capabilities_to_tools(
    capabilities: Dict[str, Capability],
) -> Iterable[openai.types.chat.completion_create_params.ChatCompletionToolParam]:
    """
    This function takes a dictionary of capabilities and returns a dictionary of functions, that can be called with the
    parameters of the respective capabilities.
    """
    return [
        ChatCompletionToolParam(
            type="function",
            function=Function(
                name=name,
                description=capability.describe(),
                parameters=capability.to_model().model_json_schema(schema_generator=OptimizedSchemaGenerator),
            ),
        )
        for name, capability in capabilities.items()
    ]


def function_call_capability(
    function: Callable[..., Awaitable[str]], description: str, name: str | None = None, bind_self: Any | None = None
) -> Capability:
    class FunctionCapability(Capability):
        @override
        def describe(self) -> str:
            return description

        @override
        async def __call__(self, *args, **kwargs) -> str:
            raise NotImplementedError("Internal Error: Could not assign function call capability")

    if name is None:
        name = function.__name__

    if bind_self is not None:
        function = partial(function, bind_self)

    orig_sig = inspect.signature(function)
    new_params = (
        inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        *orig_sig.parameters.values(),
    )
    new_sig = inspect.Signature(parameters=new_params, return_annotation=orig_sig.return_annotation)

    async def __call__(self, *args, **kwargs) -> str:
        return await function(*args, **kwargs)

    __call__: Callable[..., Awaitable[str]] = wraps(function)(__call__)
    __call__.__signature__ = new_sig

    FunctionCapability.__name__ = name
    FunctionCapability.__qualname__ = name
    FunctionCapability.__call__ = __call__

    return FunctionCapability()
