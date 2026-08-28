import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hackingBuddyGPT.utils.web_api.response_analyzer_with_llm import ResponseAnalyzerWithLLM
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose


class TestResponseAnalyzerWithLLM(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock()
        self.capabilities = {"http_request": MagicMock()}
        self.pentesting_info = MagicMock()
        self.prompt_helper = MagicMock()
        self.analyzer = ResponseAnalyzerWithLLM(
            purpose=PromptPurpose.PARSING,
            llm=self.llm,
            capabilities=self.capabilities,
            pentesting_info=self.pentesting_info,
            capacity=MagicMock(),
            prompt_helper=self.prompt_helper
        )

    def test_parse_http_response_success(self):
        raw_response = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            '{"id": 1, "name": "John"}'
        )

        status_code, headers, body = self.analyzer.parse_http_response(raw_response)

        self.assertEqual(status_code, "200")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(body, {"id": 1, "name": "John"})

    def test_parse_http_response_html(self):
        raw_response = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "\n"
            "<!DOCTYPE html><html><body>Error Page</body></html>"
        )

        status_code, headers, body = self.analyzer.parse_http_response(raw_response)

        self.assertEqual(status_code, "200")
        self.assertEqual(headers["Content-Type"], "text/html")
        self.assertEqual(body, "")

    def test_process_step_calls_llm(self):
        step = "Please analyze the response"
        prompt_history = []
        capability = "http_request"

        tool_call = MagicMock()
        tool_call.id = "abc123"
        tool_call.function.arguments = "{}"
        message = MagicMock()
        message.tool_calls = [tool_call]
        llm_result = MagicMock()
        llm_result.result = message
        self.llm.get_response = MagicMock(return_value=llm_result)

        fake_response = MagicMock()
        fake_response.execute = AsyncMock(return_value="Execution Result")

        with patch(
            "hackingBuddyGPT.utils.web_api.response_analyzer_with_llm.tool_call_to_action",
            return_value=fake_response,
        ):
            updated_history, result = asyncio.run(self.analyzer.process_step(step, prompt_history, capability))

        # get_response was asked to force exactly the requested capability.
        _, kwargs = self.llm.get_response.call_args
        self.assertEqual(kwargs.get("tool_choice"), "required")
        self.assertEqual(list(kwargs.get("capabilities").keys()), ["http_request"])
        self.assertIn(step, updated_history[0]["content"])
        self.assertEqual(result, "Execution Result")

    def test_get_addition_context(self):
        raw_response = (
            "HTTP/1.1 404 Not Found\n"
            "Content-Type: application/json\n"
            "{}"
        )
        step = {
            "expected_response_code": ["200", "201"],
            "security": "Ensure auth token"
        }

        status_code, additional_context, full_response = self.analyzer.get_addition_context(raw_response, step)

        self.assertEqual(status_code, "404")
        self.assertIn("Ensure auth token", additional_context)
        self.assertIn("Status Code: 404", full_response)

if __name__ == "__main__":
    unittest.main()
