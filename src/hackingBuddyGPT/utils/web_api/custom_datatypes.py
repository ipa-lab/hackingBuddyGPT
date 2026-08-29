from typing import List

from hackingBuddyGPT.utils.llm_util import Message

# A prompt is the canonical chat history: a list of message dicts (and/or litellm message objects).
Prompt = List[Message]
