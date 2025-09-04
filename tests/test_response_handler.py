import os
import unittest
from unittest.mock import MagicMock, patch

from hackingBuddyGPT.utils.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.web_api.response_handler import (
    ResponseHandler,
)
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.configuration_handler import ConfigurationHandler


class TestResponseHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler_mock = MagicMock(spec=LLMHandler)
        self.config_path = os.path.join(os.path.dirname(__file__), "test_files","test_config.json")
        self.configuration_handler = ConfigurationHandler(self.config_path)
        self.config = self.configuration_handler._load_config(self.config_path)
        self.host = "https://reqres.in"
        self.description = "Fake API"
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)
        self.response_handler = ResponseHandler(self.llm_handler_mock,  PromptContext.DOCUMENTATION, self.config,
                 self.prompt_helper, None)


    def test_parse_http_status_line_valid(self):
        status_line = "HTTP/1.1 200 OK"
        result = self.response_handler.parse_http_status_line(status_line)
        self.assertEqual(result, "200 OK")

    def test_parse_http_status_line_invalid(self):
        status_line = "Invalid status line"
        with self.assertRaises(ValueError):
            self.response_handler.parse_http_status_line(status_line)

    def test_extract_response_example(self):
        html_content = """
        <html>
            <body>
                <code id="example">{"example": "test"}</code>
                <code id="result">{"key": "value"}</code>
            </body>
        </html>
        """
        result = self.response_handler.extract_response_example(html_content)
        self.assertEqual(result, {"key": "value"})

    def test_extract_response_example_invalid(self):
        html_content = "<html><body>No code tags</body></html>"
        result = self.response_handler.extract_response_example(html_content)
        self.assertIsNone(result)

    @patch(
        "hackingBuddyGPT.usecases.web_api_testing.response_processing.ResponseHandler.parse_http_response_to_openapi_example"
    )
    def test_parse_http_response_to_openapi_example(self, mock_parse_http_response_to_schema):
        openapi_spec = {"components": {"schemas": {}}}
        http_response = 'HTTP/1.1 200 OK\r\n\r\n{"id": 1, "name": "test"}'
        path = "/test"
        method = "GET"

        mock_parse_http_response_to_schema.return_value = ("#/components/schemas/Test", "Test", openapi_spec)

        entry_dict, reference, updated_spec = self.response_handler.parse_http_response_to_openapi_example(
            openapi_spec, http_response, path, method
        )

        self.assertEqual(reference, "Test")
        self.assertEqual(updated_spec, openapi_spec)
        self.assertIn("Test", entry_dict)

    def test_extract_description(self):
        note = MagicMock()
        note.action.content = "Test description"
        description = self.response_handler.extract_description(note)
        self.assertEqual(description, "Test description")

    from unittest.mock import patch

    @patch("hackingBuddyGPT.usecases.web_api_testing.response_processing.ResponseHandler.parse_http_response_to_schema")
    def test_parse_http_response_to_schema(self, mock_parse_http_response_to_schema):
        openapi_spec = {"components": {"schemas": {}}}
        body_dict = {"id": 1, "name": "test"}
        path = "/tests"

        def mock_side_effect(spec, body, path):
            schema_name = "Test"
            spec["components"]["schemas"][schema_name] = {
                "type": "object",
                "properties": {key: {"type": type(value).__name__, "example": value} for key, value in body.items()},
            }
            reference = f"#/components/schemas/{schema_name}"
            return reference, schema_name, spec

        mock_parse_http_response_to_schema.side_effect = mock_side_effect

        reference, object_name, updated_spec = self.response_handler.parse_http_response_to_schema(
            openapi_spec, body_dict, path
        )

        self.assertEqual(reference, "#/components/schemas/Test")
        self.assertEqual(object_name, "Test")
        self.assertIn("Test", updated_spec["components"]["schemas"])
        self.assertIn("id", updated_spec["components"]["schemas"]["Test"]["properties"])
        self.assertIn("name", updated_spec["components"]["schemas"]["Test"]["properties"])

    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="yaml_content")
    def test_read_yaml_to_string(self, mock_open):
        filepath = "test.yaml"
        result = self.response_handler.read_yaml_to_string(filepath)
        mock_open.assert_called_once_with(filepath, "r")
        self.assertEqual(result, "yaml_content")

    def test_read_yaml_to_string_file_not_found(self):
        filepath = "nonexistent.yaml"
        result = self.response_handler.read_yaml_to_string(filepath)
        self.assertIsNone(result)

    def test_extract_endpoints(self):
        note = "1. GET /test\n"
        result = self.response_handler.extract_endpoints(note)
        self.assertEqual({"/test": ["GET"]}, result)

    def test_extract_keys(self):
        key = "name"
        value = "test"
        properties_dict = {}
        result = self.response_handler.extract_keys(key, value, properties_dict)
        self.assertIn(key, result)
        self.assertEqual(result[key], {"type": "str", "example": "test"})


if __name__ == "__main__":
    unittest.main()
