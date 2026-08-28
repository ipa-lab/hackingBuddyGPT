import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hackingBuddyGPT.usecases.web_api.simple_openapi_documentation import (
    SimpleWebAPIDocumentation,
)
from hackingBuddyGPT.utils import Console
from hackingBuddyGPT.utils.logging import JsonlLogger


class TestSimpleWebAPIDocumentationTest(unittest.TestCase):
    def setUp(self):
        # A stand-in LLM; the actual LLM calls are mocked at the LLMHandler boundary per test.
        self.mock_llm = MagicMock()
        console = Console()

        log = JsonlLogger(
            console=console,
            log_dir=tempfile.mkdtemp(),
            tag="webApiDocumentation",
        )
        config_path = os.path.join(os.path.dirname(__file__), "test_files", "test_config.json")

        self.agent = SimpleWebAPIDocumentation(llm=self.mock_llm, log=log, config_path=config_path,
                                               strategy_string="cot")
        self.agent.init()

    def test_initial_prompt(self):
        # Test if the initial prompt is set correctly
        expected_prompt = "You're tasked with documenting the REST APIs of a website hosted at https://jsonplaceholder.typicode.com/. The website is See https://jsonplaceholder.typicode.com/. Start with an empty OpenAPI specification and be meticulous in documenting your observations as you traverse the APIs"

        self.assertIn(expected_prompt, self.agent._prompt_history[0]["content"])

    def test_all_flags_found(self):
        # Mock console.print to suppress output during testing
        with patch("rich.console.Console.print"):
            self.agent.all_http_methods_found(1)
            self.assertFalse(self.agent.all_http_methods_found(1))

    @patch("time.perf_counter", side_effect=[1, 2])  # Mocking perf_counter for consistent timing
    def test_perform_round(self, mock_perf_counter):
        # The detection loop now uses llm.get_response(tool_choice="required") and rebuilds the
        # un-executed action via tool_call_to_action; the FSM/handle_response are unchanged.
        tool_call = MagicMock()
        tool_call.id = "tool_call_1"
        tool_call.function.arguments = "{}"
        message = MagicMock()
        message.role = "assistant"
        message.content = "Mocked LLM response"
        message.tool_calls = [tool_call]
        llm_result = MagicMock()
        llm_result.result = message
        llm_result.total_tokens = 5
        llm_result.cost = 0.0

        self.agent.llm.get_response = MagicMock(return_value=llm_result)
        self.agent.log.call_response = AsyncMock(return_value=1)
        self.agent.log.add_tool_call = AsyncMock()

        # The rebuilt action + its execution result.
        mock_response = MagicMock()
        real_http_response = (
            "HTTP/1.1 200 OK\r\n"
            "Date: Fri, 18 Apr 2025 07:31:21 GMT\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "Transfer-Encoding: chunked\r\n"
            "Connection: keep-alive\r\n"
            "Content-Encoding: gzip\r\n"
            "\r\n"
            '{"page":1,"per_page":6,"total":12,"total_pages":2,"data":[{"id":1,"name":"cerulean"}]}'
        )
        mock_response.execute = AsyncMock(return_value=real_http_response)
        mock_response.action.path = "/posts/"

        self.agent.prompt_helper.found_endpoints = ["/users/"]
        with patch(
            "hackingBuddyGPT.usecases.web_api.simple_openapi_documentation.tool_call_to_action",
            return_value=mock_response,
        ):
            result = asyncio.run(self.agent.perform_round(1))

        # Assertions
        self.assertFalse(result)

        # The model was asked with a forced tool choice.
        self.assertGreaterEqual(self.agent.llm.get_response.call_count, 1)
        _, kwargs = self.agent.llm.get_response.call_args
        self.assertEqual(kwargs.get("tool_choice"), "required")
        # Check if the prompt history was updated correctly
        self.assertGreaterEqual(len(self.agent._prompt_history), 1)  # Initial message + LLM response + tool message


if __name__ == "__main__":
    unittest.main()
