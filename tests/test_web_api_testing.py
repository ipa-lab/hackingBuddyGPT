import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hackingBuddyGPT.usecases.web_api.simple_web_api_testing import (
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
        # The testing round now runs on the standard loop: llm.get_response(tool_choice="required")
        # returns an assistant message with a tool call, which is executed via the CapabilityManager.
        tool_call = MagicMock()
        tool_call.id = "tool_call_1"
        tool_call.function.name = "ProposedHTTPRequest"
        tool_call.function.arguments = '{"method": "GET", "path": "/users/"}'

        message = MagicMock()
        message.tool_calls = [tool_call]

        llm_result = MagicMock()
        llm_result.result = message
        llm_result.total_tokens = 5
        llm_result.cost = 0.0

        # Mock the LLM boundary (get_response) and the pieces that need a live run/network:
        self.agent.llm.get_response = MagicMock(return_value=llm_result)
        self.agent.log.call_response = AsyncMock(return_value=1)
        self.agent._capabilities.run_capability_json = AsyncMock(return_value=(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n\r\n"
            '{"id": 1, "username": "alice@example.com", "token": "eyJhbGciOi..."}'
        ))
        # The LLM-driven response analysis is exercised by its own tests; stub it here.
        self.agent._response_handler.evaluate_result = AsyncMock(return_value=([], "200"))

        # Perform the round
        result = asyncio.run(self.agent.perform_round(1))

        # Assertions
        self.assertFalse(result)  # No flags found in this round

        # The standard loop was driven: the model was asked and the tool call was executed.
        self.assertGreaterEqual(self.agent.llm.get_response.call_count, 1)
        self.assertGreaterEqual(self.agent._capabilities.run_capability_json.call_count, 1)
        # get_response must force exactly the proposed-request capability.
        _, kwargs = self.agent.llm.get_response.call_args
        self.assertEqual(kwargs.get("tool_choice"), "required")
        self.assertEqual(list(kwargs.get("capabilities").keys()), ["ProposedHTTPRequest"])
        # Check if the prompt history was updated correctly
        self.assertGreaterEqual(len(self.agent._prompt_history), 1)  # Initial message + LLM response + tool message


if __name__ == "__main__":
    unittest.main()
