import abc
import inspect
from typing import Union, Type

from pydantic import create_model, BaseModel


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
    def describe(self, name: str = None) -> str:
        """
        describe should return a string that describes the capability. This is used to generate the help text for the
        LLM.
        I don't like, that at the moment the name under which the capability is available to the LLM is allowed to be
        passed in, but it is necessary at the moment, to be backwards compatible. Please do not use the name if you
        don't really have to, then we can see if we can remove it in the future.

        This is a method and not just a simple property on purpose (though it could become a @property in the future, if
        we don't need the name parameter anymore), so that it can template in some of the capabilities parameters into
        the description.
        """
        pass

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        """
        The actual execution of a capability, please make sure, that the parameters and return type of your
        implementation are well typed, as this will make it easier to support full function calling soon.
        """
        pass

    def to_instructor(self, name: str):
        sig = inspect.signature(self.__call__)
        fields = {param: (param_info.annotation, ...) for param, param_info in sig.parameters.items()}
        model_type = create_model(self.__class__.__name__, __doc__=self.describe(name), **fields)

        def execute(model):
            return self(**model.dict())
        model_type.execute = execute

        return model_type


class Action(BaseModel):
    action: BaseModel


def capabilities_to_instructor(capabilities: dict) -> Type[Action]:
    class Model(Action):
        action: Union[tuple([capability.to_instructor(name) for name, capability in capabilities.items()])]

        def execute(self):
            return self.action.execute()

    return Model

