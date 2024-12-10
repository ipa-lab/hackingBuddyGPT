import unittest
from unittest.mock import MagicMock, patch

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.usecases.web_api_testing.documentation.openapi_specification_handler import (
    OpenAPISpecificationHandler,
)


class TestSpecificationHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock()
        self.response_handler = MagicMock()
        self.doc_handler = OpenAPISpecificationHandler(self.llm_handler, self.response_handler)

    @patch("os.makedirs")
    @patch("builtins.open")
    def test_write_openapi_to_yaml(self, mock_open, mock_makedirs):
        self.doc_handler.write_openapi_to_yaml()
        mock_makedirs.assert_called_once_with(self.doc_handler.file_path, exist_ok=True)
        mock_open.assert_called_once_with(self.doc_handler.file, "w")

        # Create a mock HTTPRequest object
        response_mock = MagicMock()
        response_mock.action = HTTPRequest(
            host="https://jsonplaceholder.typicode.com", follow_redirects=False, use_cookie_jar=True
        )
        response_mock.action.method = "GET"
        response_mock.action.path = "/test"

        result = '{"key": "value"}'

        self.response_handler.parse_http_response_to_openapi_example = MagicMock(
            return_value=({}, "#/components/schemas/TestSchema", self.doc_handler.openapi_spec)
        )

        endpoints = self.doc_handler.update_openapi_spec(response_mock, result)

        self.assertIn("/test", self.doc_handler.openapi_spec["endpoints"])
        self.assertIn("get", self.doc_handler.openapi_spec["endpoints"]["/test"])
        self.assertEqual(
            self.doc_handler.openapi_spec["endpoints"]["/test"]["get"]["summary"], "GET operation on /test"
        )
        self.assertEqual(endpoints, ["/test"])

    def test_partial_match(self):
        string_list = ["test_endpoint", "another_endpoint"]
        self.assertTrue(self.doc_handler.is_partial_match("test", string_list))
        self.assertFalse(self.doc_handler.is_partial_match("not_in_list", string_list))


if __name__ == "__main__":
    unittest.main()
