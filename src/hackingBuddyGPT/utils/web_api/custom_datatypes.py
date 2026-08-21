from typing import Any, List

from hackingBuddyGPT.utils.llm_util import Message

# Type aliases for readability. A prompt is the canonical chat history: a list of message
# dicts (and/or litellm message objects); Context is opaque per-use-case state.
Prompt = List[Message]
Context = Any
