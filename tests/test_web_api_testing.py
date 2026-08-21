import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hackingBuddyGPT.usecases.web_api_testing.simple_web_api_testing import (
    SimpleWebAPITesting,
)
from hackingBuddyGPT.utils import Console
from hackingBuddyGPT.utils.logging import JsonlLogger


class TestSimpleWebAPITestingTest(unittest.TestCase):
    def setUp(self):
        # A stand-in LLM; the actual LLM calls are mocked at the LLMHandler boundary per test.
        self.mock_llm = MagicMock()
        console = Console()

        log = JsonlLogger(
            console=console,
            log_dir=tempfile.mkdtemp(),
        )
        config_path = os.path.join(os.path.dirname(__file__), "test_files","fakeapi_config.json")

        self.agent = SimpleWebAPITesting(llm=self.mock_llm, log=log,config_path= config_path, strategy_string= "cot")

        self.agent.init()



    def test_initial_prompt(self):
        contents = [prompt_history_entry["content"] for prompt_history_entry in self.agent._prompt_history]
        # Test if the initial prompt is set correctly
        self.assertIn(
            "You're a seasoned API tester tasked with evaluating the REST APIs of a website hosted at https://dummyjson.com. Your primary objective is to thoroughly explore the APIs, understanding their endpoints, parameters, and responses, and then devise and execute potential exploits. Be diligent in documenting your findings as you navigate through the APIs. Avoid resorting to brute-force tactics. All necessary information can be obtained from the API endpoints themselves. Remember, if you encounter an HTTP method (A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).), promptly submit it as it is of utmost importance.",
            contents,
        )

    def test_all_flags_found(self):
        # Mock console.print to suppress output during testing
        with patch("rich.console.Console.print"):
            self.agent.all_test_cases_run()
            self.assertFalse(self.agent.all_test_cases_run())

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

        # Mock the LLM handler boundary: (action, completion) as litellm tool-calling returns.
        self.agent._llm_handler.execute_prompt_with_specific_capability = MagicMock(
            return_value=(mock_response, mock_completion)
        )

        # Mock the tool execution result
        mock_response.execute = AsyncMock(return_value=(
    "HTTP/1.1 200 OK\n"
    "Date: Wed, 17 Apr 2025 12:00:00 GMT\n"
    "Content-Type: application/json; charset=utf-8\n"
    "Content-Length: 85\n"
    "Connection: keep-alive\n"
    "X-Powered-By: Express\n"
    "Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
    "Cache-Control: no-store\n"
    "Set-Cookie: sessionId=abc123; HttpOnly; Secure; Path=/\r\n\r\n"
    "\n"
    "{\n"
    '  "id": 1,\n'
    '  "username": "alice@example.com",\n'
    '  "role": "user",\n'
    '  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."\n'
    "}"
))

        mock_response.action.path = "/users/"

        # Perform the round
        result = asyncio.run(self.agent.perform_round(1))

        # Assertions
        self.assertFalse(result)  # No flags found in this round

        # Check that the LLM handler was invoked
        self.assertGreaterEqual(
            self.agent._llm_handler.execute_prompt_with_specific_capability.call_count, 1
        )
        # Check if the prompt history was updated correctly
        self.assertGreaterEqual(len(self.agent._prompt_history), 1)  # Initial message + LLM response + tool message


if __name__ == "__main__":
    unittest.main()
