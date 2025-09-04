import os
import unittest
from unittest.mock import MagicMock, patch

from hackingBuddyGPT.utils.logging import LocalLogger
from hackingBuddyGPT.usecases.web_api_documentation.simple_openapi_documentation import (
    SimpleWebAPIDocumentation,
    SimpleWebAPIDocumentationUseCase,
)
from hackingBuddyGPT.utils import Console, DbStorage


class TestSimpleWebAPIDocumentationTest(unittest.TestCase):
    @patch("hackingBuddyGPT.utils.openai.openai_lib.OpenAILib")
    def setUp(self, MockOpenAILib):
        # Mock the OpenAILib instance
        self.mock_llm = MockOpenAILib.return_value
        log_db = DbStorage(":memory:")
        console = Console()

        log_db.init()
        log = LocalLogger(
            log_db=log_db,
            console=console,
            tag="webApiDocumentation",
        )
        config_path = os.path.join(os.path.dirname(__file__), "test_files", "test_config.json")

        self.agent = SimpleWebAPIDocumentation(llm=self.mock_llm, log=log, config_path=config_path,
                                               strategy_string="cot")
        self.agent.init()
        self.simple_api_testing = SimpleWebAPIDocumentationUseCase(
            agent=self.agent
        )
        self.simple_api_testing.init()

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
        # Prepare mock responses
        mock_response = MagicMock()
        mock_completion = MagicMock()

        # Setup completion response with mocked data
        mock_completion.choices[0].message.content = "Mocked LLM response"
        mock_completion.choices[0].message.tool_calls = [MagicMock(id="tool_call_1")]
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 20

        # Mock the OpenAI LLM response
        self.agent.llm.instructor.chat.completions.create_with_completion.return_value = (
            mock_response,
            mock_completion,
        )

        # Mock the tool execution result
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

        mock_response.execute.return_value = real_http_response

        mock_response.action.path = "/posts/"

        self.agent.prompt_helper.found_endpoints = ["/users/"]
        # Perform the round
        result = self.agent.perform_round(1)


        # Assertions
        self.assertFalse(result)

        # Check if the LLM was called with the correct parameters
        mock_create_with_completion = self.agent.llm.instructor.chat.completions.create_with_completion

        # if it can be called multiple times, use assert_called
        self.assertGreaterEqual(mock_create_with_completion.call_count, 1)
        # Check if the prompt history was updated correctly
        self.assertGreaterEqual(len(self.agent._prompt_history), 1)  # Initial message + LLM response + tool message


if __name__ == "__main__":
    unittest.main()
