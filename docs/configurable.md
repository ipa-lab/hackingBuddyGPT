# Configurable

Marking a class as `@configurable` allows for the class to be configured via command line arguments or environment variables.

This is done by analyzing the parameters to the class' `__init__` method and its `__dataclass_fields__` attribute if it is a `@dataclass`.  
As having a `@configurable` also be a `@dataclass` makes it easier to extend it, it is usually recommended to define a configurable as a `@dataclass`.
Furthermore, using a dataclass allows more natural use of the `parameter()` definition.

All [use-cases](use_case.md) are automatically configurable.

## Parameter Definition

Parameters can either be defined using type hints and default values, or by using the `parameter()` method.

```python
from dataclasses import dataclass
from utils.configurable import configurable, parameter


@configurable("inner-example", "Inner Example Configurable for documentation")
@dataclass
class InnerConfigurableExample:
    text_value: str
    

@configurable("example", "Example Configurable for documentation")
@dataclass
class ConfigurableExample:
    inner_configurable: InnerConfigurableExample
    text_value: str
    number_value_with_description: int = parameter(desc="This is a number value", default=42)
    number_value_without_description: int = 43
```

As can be seen, the `parameter` method allows additionally setting a description for the parameter, while returning a `dataclasses.Field` to allow interoperability with existing tools.

The type of a configurable parameter may only be a primitive type (`int`, `str`, `bool`) or another configurable.

## Usage

When a class is marked as `@configurable`, it can be configured via command line arguments or environment variables.  
The name of the parameter is automatically built from the field name (in the case of the example to be `text_value`, `number_with_description` and `number_value_without_description`).

If a configurable has other configurable fields as parameters, they can be recursively configured, the name of the parameter is built from the field name and the field name of the inner configurable (here `inner_configurable.text_value`).

These parameters are looked up in the following order:

1. Command line arguments
2. Environment variables (with `.` being replaced with `_`)
3. .env file
4. Default values

When you have a simple use case as follows:

```python
from dataclasses import dataclass
from usecases import use_case, UseCase

@use_case("example", "Example Use Case")
@dataclass
class ExampleUseCase(UseCase):
    conf: ConfigurableExample
    
    def run(self):
        print(self.conf)
```

You can configure the `ConfigurableExample` class as follows:

```bash
echo "conf.text_value = 'Hello World'" > .env
export CONF_NUMBER_VALUE_WITH_DESCRIPTION=120
export CONF_INNER_CONFIGURABLE_TEXT_VALUE="Inner Hello World"

python3 wintermute.py example --conf.inner_configurable.text_value "Inner Hello World Overwrite"
```

This results in 

```
ConfigurableExample(
    inner_configurable=InnerConfigurableExample(text_value='Inner Hello World Overwrite'),
    text_value='Hello World',
    number_value_with_description=120,
    number_value_without_description=43
)
```

