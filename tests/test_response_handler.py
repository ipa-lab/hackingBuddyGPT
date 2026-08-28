import json
import os
import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.usecases.web_api.openapi_specification_handler import OpenAPISpecificationHandler
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PromptContext, PromptStrategy
from hackingBuddyGPT.utils.web_api.response_handler import (
    ResponseHandler,
)
from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler


class TestResponseHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler_mock = MagicMock(spec=LLMHandler)
        self.config_path = os.path.join(os.path.dirname(__file__), "test_files", "test_config.json")
        with open(self.config_path) as f:
            self.config = json.load(f)
        self.host = "https://reqres.in"
        self.description = "Fake API"
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)
        self.response_handler = ResponseHandler(self.llm_handler_mock, PromptContext.DOCUMENTATION, self.config,
                                                self.prompt_helper, None)
        # parse_http_response_* and extract_keys live on the OpenAPI spec handler.
        self.openapi_handler = OpenAPISpecificationHandler(
            llm_handler=self.llm_handler_mock,
            strategy=PromptStrategy.IN_CONTEXT,
            url=self.host,
            description=self.description,
            name="test",
        )

    def test_parse_http_status_line_valid(self):
        status_line = "HTTP/1.1 200 OK"
        result = self.response_handler.parse_http_status_line(status_line)
        self.assertEqual(result, "200 OK")

    def test_parse_http_status_line_invalid(self):
        status_line = "Invalid status line"
        with self.assertRaises(ValueError):
            self.response_handler.parse_http_status_line(status_line)

    def test_parse_http_response_to_openapi_example(self):
        openapi_spec = {"components": {"schemas": {}}}
        http_response = 'HTTP/1.1 200 OK\r\n\r\n{"id": 1, "name": "test"}'
        path = "/test"
        method = "GET"

        entry_dict, reference, updated_spec = self.openapi_handler.parse_http_response_to_openapi_example(
            openapi_spec, http_response, path, method
        )

        self.assertEqual(reference, "#/components/schemas/Test")
        self.assertIs(updated_spec, openapi_spec)
        self.assertIn("name", entry_dict)

    def test_parse_http_response_to_schema(self):
        openapi_spec = {"components": {"schemas": {}}}
        body_dict = {"id": 1, "name": "test"}
        path = "/tests"

        reference, object_name, updated_spec = self.openapi_handler.parse_http_response_to_schema(
            openapi_spec, body_dict, path
        )

        self.assertEqual(reference, "#/components/schemas/Test")
        self.assertEqual(object_name, "Test")
        self.assertIn("Test", updated_spec["components"]["schemas"])
        self.assertIn("id", updated_spec["components"]["schemas"]["Test"]["properties"])
        self.assertIn("name", updated_spec["components"]["schemas"]["Test"]["properties"])

    def test_extract_keys(self):
        key = "name"
        value = "test"
        properties_dict = {}
        result = self.openapi_handler.extract_keys(key, value, properties_dict)
        self.assertIn(key, result)
        self.assertEqual(result[key], {"type": "str", "example": "test"})


if __name__ == "__main__":
    unittest.main()
