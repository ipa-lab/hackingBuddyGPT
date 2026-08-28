import unittest
from unittest.mock import MagicMock, patch

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.utils.llm import LiteLLM


def _fake_response():
    resp = MagicMock()
    resp.choices[0].message.content = "hi"
    resp.choices[0].message.tool_calls = None
    resp.choices[0].message.reasoning_content = None
    resp.choices[0].finish_reason = "stop"
    resp.usage.prompt_tokens = 1
    resp.usage.completion_tokens = 1
    resp.usage.completion_tokens_details = None
    resp.model = "gpt-4o"
    return resp


class TestGetResponseToolChoice(unittest.TestCase):
    def setUp(self):
        self.llm = LiteLLM(api_key="k", model="gpt-4o", context_size=8192)
        self.captured = {}

        def fake_raw(messages, *, tools=None, tool_choice=None):
            self.captured["tools"] = tools
            self.captured["tool_choice"] = tool_choice
            return _fake_response()

        self.llm.raw_completion = fake_raw

    def test_tool_choice_forwarded_when_capabilities_present(self):
        caps = {"http_request": HTTPRequest("http://h")}
        with patch("litellm.completion_cost", return_value=0.0):
            self.llm.get_response([{"role": "user", "content": "x"}], capabilities=caps, tool_choice="required")
        self.assertIsNotNone(self.captured["tools"])
        self.assertEqual(self.captured["tool_choice"], "required")

    def test_tool_choice_ignored_without_tools(self):
        # No capabilities -> no tools -> a stray tool_choice must not reach the API.
        with patch("litellm.completion_cost", return_value=0.0):
            self.llm.get_response([{"role": "user", "content": "x"}], tool_choice="required")
        self.assertIsNone(self.captured["tools"])
        self.assertIsNone(self.captured["tool_choice"])


if __name__ == "__main__":
    unittest.main()
