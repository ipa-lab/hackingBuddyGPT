from enum import Enum
class PromptStrategy(Enum):
    IN_CONTEXT = 1
    CHAIN_OF_THOUGHT = 2
    TREE_OF_THOUGHT = 3

class PromptContext(Enum):
    DOCUMENTATION = 1
    PENTESTING = 2