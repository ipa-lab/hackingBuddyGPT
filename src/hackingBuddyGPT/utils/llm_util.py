import abc
import datetime
import re
import typing
from dataclasses import dataclass

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

SAFETY_MARGIN = 128
STEP_CUT_TOKENS = 128


@dataclass
class LLMResult:
    result: typing.Any
    prompt: str
    answer: str
    duration: datetime.timedelta = datetime.timedelta(0)
    tokens_query: int = 0
    tokens_response: int = 0


class LLM(abc.ABC):
    @abc.abstractmethod
    def get_response(self, prompt, *, capabilities=None, **kwargs) -> LLMResult:
        """
        get_response prompts the LLM with the given prompt and returns the result
        The capabilities parameter is not yet in use, but will be used to pass function calling style capabilities in the
        future. Please do not use it at the moment!
        """
        pass

    @abc.abstractmethod
    def encode(self, query) -> list[int]:
        pass

    def count_tokens(self, query) -> int:
        return len(self.encode(query))


def system_message(content: str) -> ChatCompletionSystemMessageParam:
    return {"role": "system", "content": content}


def user_message(content: str) -> ChatCompletionUserMessageParam:
    return {"role": "user", "content": content}


def assistant_message(content: str) -> ChatCompletionAssistantMessageParam:
    return {"role": "assistant", "content": content}


def tool_message(content: str, tool_call_id: str) -> ChatCompletionToolMessageParam:
    return {"role": "tool", "content": content, "tool_call_id": tool_call_id}


def function_message(content: str, name: str) -> ChatCompletionFunctionMessageParam:
    return {"role": "function", "content": content, "name": name}


def remove_wrapping_characters(cmd: str, wrappers: str) -> str:
    if len(cmd) < 2:
        return cmd
    if cmd[0] == cmd[-1] and cmd[0] in wrappers:
        print("will remove a wrapper from: " + cmd)
        return remove_wrapping_characters(cmd[1:-1], wrappers)
    return cmd


# often the LLM produces a wrapped command
def cmd_output_fixer(cmd: str) -> str:
    cmd = cmd.strip(" \n")
    if len(cmd) < 2:
        return cmd

    stupidity = re.compile(r"^[ \n\r]*```.*\n(.*)\n```$", re.MULTILINE)
    result = stupidity.search(cmd)
    if result:
        print("this would have been captured by the multi-line regex 1")
        cmd = result.group(1)
        print("new command: " + cmd)
    stupidity = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)
    result = stupidity.search(cmd)
    if result:
        print("this would have been captured by the multi-line regex 2")
        cmd = result.group(1)
        print("new command: " + cmd)
    stupidity = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)

    cmd = remove_wrapping_characters(cmd, "`'\"")

    if cmd.startswith("$ "):
        cmd = cmd[2:]

    return cmd


# this is ugly, but basically we only have an approximation how many tokens
# we are currently using. So we cannot just cut down to the desired size
# what we're doing is:
#   - take our current token count
#   - use the minimum of (current_count, desired count *2)
#     - this get's us roughly in the ballpark of the desired size
#     - as long as we assume that 2 * desired-count will always be larger
#       than the unschaerfe introduced by the string-.token conversion
#   - do a 'binary search' to cut-down to the desired size afterwards
#
# this should reduce the time needed to do the string->token conversion
# as this can be long-running if the LLM puts in a 'find /' output
def trim_result_front(model: LLM, target_size: int, result: str) -> str:
    cur_size = model.count_tokens(result)
    TARGET_SIZE_FACTOR = 3
    if cur_size > TARGET_SIZE_FACTOR * target_size:
        print(f"big step trim-down from {cur_size} to {2 * target_size}")
        result = result[: TARGET_SIZE_FACTOR * target_size]
        cur_size = model.count_tokens(result)

    while cur_size > target_size:
        print(f"need to trim down from {cur_size} to {target_size}")
        diff = cur_size - target_size
        step = int((diff + STEP_CUT_TOKENS) / 2)
        result = result[:-step]
        cur_size = model.count_tokens(result)

    return result
