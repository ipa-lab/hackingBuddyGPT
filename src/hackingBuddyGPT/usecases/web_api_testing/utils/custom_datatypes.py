from typing import List, Any, Union, Dict
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
# Type aliases for readability
Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any