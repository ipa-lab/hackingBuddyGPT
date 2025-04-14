import os
import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.usecases.web_api_testing.documentation import OpenAPISpecificationHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing import ResponseHandler
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler


class TestOpenAPISpecificationHandler(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock(spec=LLMHandler)
        self.response_handler = MagicMock(spec=ResponseHandler)
        self.strategy = PromptStrategy.IN_CONTEXT
        self.url = "https://reqres.in"
        self.description = "Fake API"
        self.name = "reqres"

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

        result = "HTTP/1.1 200 OK"
        self.response_handler.parse_http_response_to_openapi_example.return_value = (
            {"id": 1, "name": "John"},
            "#/components/schemas/User",
            self.openapi_handler.openapi_spec,
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

        result = "HTTP/1.1 404 Not Found"
        prompt_engineer = MagicMock()
        prompt_engineer.prompt_helper.current_step = 1

        updated_endpoints = self.openapi_handler.update_openapi_spec(mock_resp, result, prompt_engineer)

        self.assertIn("/invalid", self.openapi_handler.unsuccessful_paths)
        self.assertIn("/invalid", updated_endpoints)

if __name__ == "__main__":
    unittest.main()
