import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.utils.web_api.response_analyzer_with_llm import ResponseAnalyzerWithLLM
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose


class TestResponseAnalyzerWithLLM(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock()
        self.pentesting_info = MagicMock()
        self.prompt_helper = MagicMock()
        self.analyzer = ResponseAnalyzerWithLLM(
            purpose=PromptPurpose.PARSING,
            llm_handler=self.llm_handler,
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

    def test_process_step_calls_llm_handler(self):
        step = "Please analyze the response"
        prompt_history = []
        capability = "http_request"

        fake_response = MagicMock()
        fake_response.execute.return_value = "Execution Result"

        fake_completion = MagicMock()
        fake_completion.choices = [MagicMock(message=MagicMock(tool_calls=[MagicMock(id="abc123")]))]

        self.llm_handler.execute_prompt_with_specific_capability.return_value = (fake_response, fake_completion)

        updated_history, result = self.analyzer.process_step(step, prompt_history, capability)

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
