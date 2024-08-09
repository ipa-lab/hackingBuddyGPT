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


class PromptContext(Enum):
    """
    Enumeration for different contexts in which prompts are generated.

    Attributes:
        DOCUMENTATION (int): Represents the documentation context.
        PENTESTING (int): Represents the penetration testing context.
    """
    DOCUMENTATION = 1
    PENTESTING = 2
