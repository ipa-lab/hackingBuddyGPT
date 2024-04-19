# Use Cases

Wintermute consists of different use-cases (classes extending `UseCase`, being annotated with `@use_case` and being imported somewhere from the main `wintermute.py` file), which can be run individually.

The `@use_case` annotation takes a name and description as arguments, which are then used for the sub-commands in the command line interface.

When building a use-case, the `run` method must be implemented, which is called after calling the (optional) `init` method (note that this is not the `__init__` method).  
The `run` method should contain the main logic of the use-case, though it is recommended to split the logic into smaller methods that are called from `run` for better readability (see the code for [`RoundBasedUseCase`](#round-based-use-case) for an example).

A use-case is automatically a `configurable`, which means, that all parameters of its `__init__` function (or fields for dataclasses) can be set via command line / environment parameters. For more information read the [configurable](configurable.md) documentation.  
It is recommended to define a use case to be a `@dataclass`, so that all parameters are directly visible, and the use-case can be easily extended.

## General Use Cases

Usually a use case follows the pattern, that it has a connections to the log database, a LLM and a system with which it is interacting.

The LLM should be defined as closely as necessary for the use case, as prompt templates are dependent on the LLM in use.  
If you don't yet want to specify eg. `GPT4Turbo`, you can use `llm: OpenAIConnection`, and dynamically specify the LLM to be used in the parameters `llm.model` and `llm.context_size`.

In addition to that, arbitrary parameters and flags can be defined, with which to control the use-case. For consistency reasons please take a look if similar parameters are used in other use cases, and try to have them act accordingly.

When interacting with a LLM, the prompt and output should always be logged `add_log_query`, `add_log_analyze_response`, `add_log_update_state` or alike, to record all interactions.

## Round Based Use Case

The `RoundBasedUseCase` is an abstract base class for use-cases that are based on rounds where the LLM is called with a certain input and the result is evaluated using different capabilities.

An implementation needs to implement the `perform_round` method, which is called for each round. It can also optionally implement the `setup` and `teardown` methods, which are called before and after the rounds, respectively.
