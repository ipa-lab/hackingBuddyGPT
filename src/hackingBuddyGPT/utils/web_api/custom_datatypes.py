from typing import Any, List, Union

from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageParam

# Type aliases for readability
Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any
