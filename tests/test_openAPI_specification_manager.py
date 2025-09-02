import os
import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.usecases.web_api_testing.documentation import OpenAPISpecificationHandler
from hackingBuddyGPT.utils.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PromptStrategy, PromptContext
from hackingBuddyGPT.usecases.web_api_testing.response_processing import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.configuration_handler import ConfigurationHandler


class TestOpenAPISpecificationHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock(spec=LLMHandler)
        self.llm_handler_mock = MagicMock()
        self.response_handler = MagicMock(spec=ResponseHandler)
        self.strategy = PromptStrategy.IN_CONTEXT
        self.url = "https://jsonplaceholder.typicode.com/"
        self.description = "JSON Placeholder API"
        self.name = "JSON Placeholder API"
        self.llm_handler_mock = MagicMock(spec=LLMHandler)
        self.config_path = os.path.join(os.path.dirname(__file__), "test_files", "test_config.json")
        self.configuration_handler = ConfigurationHandler(self.config_path)
        self.config = self.configuration_handler._load_config(self.config_path)
        self.host = "https://jsonplaceholder.typicode.com/"
        self.description = "JSON Placeholder API"
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)
        self.response_handler = ResponseHandler(self.llm_handler_mock, PromptContext.DOCUMENTATION, self.config,
                                                self.prompt_helper, None)
        self.openapi_handler = OpenAPISpecificationHandler(
            llm_handler=self.llm_handler,
            response_handler=self.response_handler,
            strategy=self.strategy,
            url=self.url,
            description=self.description,
            name=self.name,
        )

    def test_update_openapi_spec_success(self):
        # Mock HTTP Request object
        mock_request = MagicMock()
        mock_request.__class__.__name__ = "HTTPRequest"
        mock_request.path = "/users"
        mock_request.method = "GET"

        # Mock Response object
        mock_resp = MagicMock()
        mock_resp.action = mock_request

        result = (
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
)

        prompt_engineer = MagicMock()
        prompt_engineer.prompt_helper.current_step = 1  # Needed for replace_id_with_placeholder

        updated_endpoints = self.openapi_handler.update_openapi_spec(mock_resp, result, prompt_engineer)

        self.assertIn("/users", updated_endpoints)
        self.assertIn("GET", self.openapi_handler.endpoint_methods["/users"])
        self.assertEqual(self.openapi_handler.openapi_spec["endpoints"]["/users"]["get"]["summary"], "GET operation on /users")

    def test_update_openapi_spec_unsuccessful(self):
        mock_request = MagicMock()
        mock_request.__class__.__name__ = "HTTPRequest"
        mock_request.path = "/invalid"
        mock_request.method = "POST"

        mock_resp = MagicMock()
        mock_resp.action = mock_request

        result = (
            "HTTP/1.1 404 Not Found\n"
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
            '  "msg": "error not found"'
            "}"
        )
        prompt_engineer = MagicMock()
        prompt_engineer.prompt_helper.current_step = 1
        self.openapi_handler.openapi_spec = {
            "endpoints": {
                "/invalid": {
                    "get": {
                        "id": "id"
                    }
                }
            }
        }
        updated_endpoints = self.openapi_handler.update_openapi_spec(mock_resp, result, prompt_engineer)

        self.assertIn("/invalid", self.openapi_handler.unsuccessful_paths)
        self.assertIn("/invalid", updated_endpoints)

    def test_extract_status_code_and_message_valid(self):
        result = "HTTP/1.1 200 OK\nContent-Type: application/json"
        code, message = self.openapi_handler.extract_status_code_and_message(result)
        self.assertEqual(code, "200")
        self.assertEqual(message, "OK")

    def test_extract_status_code_and_message_invalid(self):
        result = "Not an HTTP header"
        code, message = self.openapi_handler.extract_status_code_and_message(result)
        self.assertIsNone(code)
        self.assertIsNone(message)

    def test_get_type_integer(self):
        self.assertEqual(self.openapi_handler.get_type("123"), "integer")

    def test_get_type_double(self):
        self.assertEqual(self.openapi_handler.get_type("3.14"), "double")

    def test_get_type_string(self):
        self.assertEqual(self.openapi_handler.get_type("hello"), "string")

    def test_replace_crypto_with_id_found(self):
        path = "/currency/bitcoin/prices"
        replaced = self.openapi_handler.replace_crypto_with_id(path)
        self.assertIn("{id}", replaced)

    def test_replace_crypto_with_id_not_found(self):
        path = "/currency/euro/prices"
        replaced = self.openapi_handler.replace_crypto_with_id(path)
        self.assertEqual(replaced, path)

    def test_replace_id_with_placeholder_basic(self):
        path = "/user/1/orders"
        mock_prompt_engineer = MagicMock()
        mock_prompt_engineer.prompt_helper.current_step = 1
        result = self.openapi_handler.replace_id_with_placeholder(path, mock_prompt_engineer)
        self.assertIn("{id}", result)

    def test_replace_id_with_placeholder_current_step_2(self):
        path = "/user/1234/orders"
        mock_prompt_engineer = MagicMock()
        mock_prompt_engineer.prompt_helper.current_step = 2
        result = self.openapi_handler.replace_id_with_placeholder(path, mock_prompt_engineer)
        self.assertTrue(result.startswith("user"))

    def test_is_partial_match_true(self):
        self.assertTrue(self.openapi_handler.is_partial_match("/users/1", ["/users/{id}"]))

    def test_is_partial_match_false(self):
        self.assertFalse(self.openapi_handler.is_partial_match("/admin", ["/users/{id}", "/posts"]))

    if __name__ == "__main__":
        unittest.main()


if __name__ == "__main__":
    unittest.main()
