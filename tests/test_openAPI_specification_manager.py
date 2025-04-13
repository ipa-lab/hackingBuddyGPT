from unittest.mock import MagicMock, patch

import unittest
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.usecases.web_api_testing.documentation import OpenAPISpecificationHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation import PromptEngineer
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.response_processing import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy
from hackingBuddyGPT.capabilities.yamlFile import YAMLFile
from hackingBuddyGPT.usecases.web_api_testing.documentation.pattern_matcher import PatternMatcher

class TestSpecificationHandler(unittest.TestCase):

    def setUp(self):
        llm_handler_mock = MagicMock(spec=LLMHandler)
        response_handler_mock =MagicMock(spec=ResponseHandler)
        prompt_strategy_mock =MagicMock(spec=PromptStrategy).CHAIN_OF_THOUGHT
        self.response_handler = MagicMock(spec=ResponseHandler)
        self.doc_handler = OpenAPISpecificationHandler(
                llm_handler=llm_handler_mock,
                response_handler=response_handler_mock,
                strategy=prompt_strategy_mock,
                url="https://fakeapi.com",
                description="A sample API",
                name="FakeAPI"
            )
        self.doc_handler._capabilities['yaml'] = MagicMock(spec=YAMLFile)
        self.doc_handler.pattern_matcher = MagicMock(spec=PatternMatcher)

    @patch("builtins.open", new_callable=MagicMock)
    def test_write_openapi_to_yaml(self, mock_open, mock_makedirs):
        # Simulate writing the OpenAPI spec to a YAML file
        self.doc_handler.write_openapi_to_yaml()
        mock_makedirs.assert_called_once_with(self.doc_handler.file_path, exist_ok=True)
        mock_open.assert_called_once_with(self.doc_handler.file, "w")

    def test_update_openapi_spec(self):
        # Create a mock HTTPRequest object
        request_mock = MagicMock(spec=HTTPRequest)
        request_mock.path = "/test"
        request_mock.method = "GET"

        response_mock = MagicMock()
        response_mock.action = request_mock

        result = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"key": "value"}'

        # Setup the mock to return a tuple as expected by the method being tested
        self.response_handler.parse_http_response_to_openapi_example.return_value = (
            {}, "#/components/schemas/TestSchema", self.doc_handler.openapi_spec
        )
        prompt_engineer =MagicMock(spec=PromptEngineer)


        # Run the method under test
        endpoints = self.doc_handler.update_openapi_spec(response_mock, result, prompt_engineer)

        # Assertions to verify the behavior
        self.assertIn("/test", self.doc_handler.openapi_spec["endpoints"])
        self.assertIn("get", self.doc_handler.openapi_spec["endpoints"]["/test"])
        self.assertEqual(
            self.doc_handler.openapi_spec["endpoints"]["/test"]["get"]["summary"],
            "GET operation on /test"
        )
        self.assertEqual(endpoints, ["/test"])

    def test_partial_match(self):
        # Test partial match functionality
        string_list = ["test_endpoint", "another_endpoint"]
        self.assertTrue(self.doc_handler.is_partial_match("test", string_list))
        self.assertFalse(self.doc_handler.is_partial_match("not_in_list", string_list))


if __name__ == "__main__":
    unittest.main()
