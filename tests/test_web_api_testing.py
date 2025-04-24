import unittest
from unittest.mock import MagicMock, patch

from hackingBuddyGPT.usecases import SimpleWebAPITesting
from hackingBuddyGPT.utils.logging import LocalLogger
from hackingBuddyGPT.usecases.web_api_testing.simple_web_api_testing import (
    SimpleWebAPITestingUseCase,
)
from hackingBuddyGPT.utils import Console, DbStorage


class TestSimpleWebAPITestingTest(unittest.TestCase):
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
            tag="integration_test_linuxprivesc",
        )
        self.agent = SimpleWebAPITesting(llm=self.mock_llm, log=log)
        self.agent.init()
        self.simple_api_testing = SimpleWebAPITestingUseCase(
            agent=self.agent,
            log=log,
            max_turns=len(self.mock_llm.responses),
        )
        self.simple_api_testing.init()

    def test_initial_prompt(self):
        # Test if the initial prompt is set correctly
        self.assertIn(
            "You're a seasoned API tester tasked with evaluating the REST APIs of a website hosted at https://jsonplaceholder.typicode.com. Your primary objective is to thoroughly explore the APIs, understanding their endpoints, parameters, and responses, and then devise and execute potential exploits. Be diligent in documenting your findings as you navigate through the APIs. Avoid resorting to brute-force tactics. All necessary information can be obtained from the API endpoints themselves. Remember, if you encounter an HTTP method (A string that represents an HTTP method (e.g., 'GET', 'POST', etc.).), promptly submit it as it is of utmost importance.",
            self.agent._prompt_history[0]["content"],
        )

    def test_all_flags_found(self):
        # Mock console.print to suppress output during testing
        with patch("rich.console.Console.print"):
            self.agent.all_http_methods_found()
            self.assertFalse(self.agent.all_http_methods_found())

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
        mock_response.execute.return_value = "HTTP/1.1 200 OK"
        mock_response.action.path = "/users/"

        # Perform the round
        result = self.agent.perform_round(1)

        # Assertions
        self.assertFalse(result)  # No flags found in this round

        # Check if the LLM was called with the correct parameters
        mock_create_with_completion = self.agent.llm.instructor.chat.completions.create_with_completion

        # if it can be called multiple times, use assert_called
        self.assertGreaterEqual(mock_create_with_completion.call_count, 1)
        # Check if the prompt history was updated correctly
        self.assertGreaterEqual(len(self.agent._prompt_history), 1)  # Initial message + LLM response + tool message


if __name__ == "__main__":
    unittest.main()
