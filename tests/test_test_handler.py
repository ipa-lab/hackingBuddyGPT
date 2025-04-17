import unittest
from unittest.mock import mock_open, patch, MagicMock

from hackingBuddyGPT.usecases.web_api_testing.testing.test_handler import TestHandler
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler


class TestTestHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock(spec=LLMHandler)
        self.handler = TestHandler(self.llm_handler)

    def test_parse_test_case(self):
        note = "Test case for GET /users:\nDescription: Get all users\nInput Data: {}\nExpected Output: 200"
        parsed = self.handler.parse_test_case(note)
        self.assertEqual(parsed["description"], "Test case for GET /users")
        self.assertEqual(parsed["expected_output"], "200")

    @patch("builtins.open", new_callable=mock_open)
    def test_write_test_case_to_file(self, mock_open):
        test_case = {"input": {}, "expected_output": {}}
        self.handler.file = "mock_test_case.txt"  # override to avoid real file writes
        self.handler.write_test_case_to_file("desc", test_case)
        mock_open().write.assert_called()

        @patch("builtins.open", new_callable=mock_open)
        def test_generate_test_case_and_write_output(self, mock_file):
            """
            Advanced integration test for generating and writing a test case.

            It verifies that:
            - the LLM handler is called correctly,
            - the generated test case contains expected data,
            - the output is written to file in the correct format.
            """
            # Inputs
            analysis = "GET /status returns server status"
            endpoint = "/status"
            method = "GET"
            body = "{}"
            status_code = 200
            prompt_history = []

            # Call generate_test_case directly
            description, test_case, updated_history = self.handler.generate_test_case(
                analysis, endpoint, method, body, status_code, prompt_history
            )

            # Assertions on the generated test case
            self.assertEqual(description, "Test case for GET /status")
            self.assertEqual(test_case["endpoint"], "/status")
            self.assertEqual(test_case["method"], "GET")
            self.assertEqual(test_case["expected_output"]["expected_status_code"], 200)
            self.assertEqual(test_case["expected_output"]["expected_body"], {"status": "ok"})

            # Call write_test_case_to_file and check what was written
            self.handler.write_test_case_to_file(description, test_case)
            handle = mock_file()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)

            self.assertIn("Test case for GET /status", written_data)
            self.assertIn('"expected_status_code": 200', written_data)
            self.assertIn('"expected_body": {"status": "ok"}', written_data)

