from enum import Enum


class PromptStrategy(Enum):
    """
    Enumeration for different prompt engineering strategies.

    Attributes:
        IN_CONTEXT (int): Represents the in-context learning strategy.
        CHAIN_OF_THOUGHT (int): Represents the chain-of-thought strategy.
        TREE_OF_THOUGHT (int): Represents the tree-of-thought strategy.
    """

    IN_CONTEXT = 1
    CHAIN_OF_THOUGHT = 2
    TREE_OF_THOUGHT = 3


def strategy_from_string(strategy_string: str) -> "PromptStrategy":
    """Map a short strategy string to a :class:`PromptStrategy`.

    ``"cot"`` -> chain-of-thought, ``"tot"`` -> tree-of-thought, ``"icl"`` ->
    in-context; anything else (including an empty string) defaults to in-context.
    """
    strategies = {
        "cot": PromptStrategy.CHAIN_OF_THOUGHT,
        "tot": PromptStrategy.TREE_OF_THOUGHT,
        "icl": PromptStrategy.IN_CONTEXT,
    }
    return strategies.get(strategy_string, PromptStrategy.IN_CONTEXT)


class PromptContext(Enum):
    """
    Enumeration for general contexts in which prompts are generated.

    Attributes:
        DOCUMENTATION (int): Represents the documentation context.
        PENTESTING (int): Represents the penetration testing context.
    """

    DOCUMENTATION = 1
    PENTESTING = 2


class PlanningType(Enum):
    """
    Enumeration for planning type in which prompts are generated.

    Attributes:
        TASK_PLANNING (int): Represents the task planning context.
        STATE_PLANNING (int): Represents the state planning context.
    """

    TASK_PLANNING = 1
    STATE_PLANNING = 2


class PromptPurpose(Enum):
    """
    Enum representing various purposes for prompt testing in security assessments.
    Each purpose is associated with a unique integer value.
    """

    # Documentation related purposes
    VERIY_SETUP = 17
    SETUP = 16
    SPECIAL_AUTHENTICATION = 0
    DOCUMENTATION = 1

    # Security related purposes
    AUTHENTICATION = 2
    AUTHORIZATION = 3
    INPUT_VALIDATION = 4
    ERROR_HANDLING_INFORMATION_LEAKAGE = 5
    SESSION_MANAGEMENT = 6
    CROSS_SITE_SCRIPTING = 7
    CROSS_SITE_FORGERY = 8
    BUSINESS_LOGIC_VULNERABILITIES = 9
    RATE_LIMITING_THROTTLING = 10
    SECURITY_MISCONFIGURATIONS = 11
    LOGGING_MONITORING = 12

    # Analysis
    PARSING = 13
    ANALYSIS = 14
    REPORTING = 15
