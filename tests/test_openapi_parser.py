import unittest
from unittest.mock import mock_open, patch

import yaml

from hackingBuddyGPT.usecases.web_api_testing.documentation.parsing import (
    OpenAPISpecificationParser,
)


class TestOpenAPISpecificationParser(unittest.TestCase):
    def setUp(self):
        self.filepath = "dummy_path.yaml"
        self.yaml_content = """
        openapi: 3.0.0
        info:
          title: Sample API
          version: 1.0.0
        servers:
          - url: https://api.example.com
          - url: https://staging.api.example.com
        paths:
          /pets:
            get:
              summary: List all pets
              responses:
                '200':
                  description: A paged array of pets
            post:
              summary: Create a pet
              responses:
                '200':
                  description: Pet created
          /pets/{petId}:
            get:
              summary: Info for a specific pet
              responses:
                '200':
                  description: Expected response to a valid request
        """

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch(
        "yaml.safe_load",
        return_value=yaml.safe_load(
            """
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0
    servers:
      - url: https://api.example.com
      - url: https://staging.api.example.com
    paths:
      /pets:
        get:
          summary: List all pets
          responses:
            '200':
              description: A paged array of pets
        post:
          summary: Create a pet
          responses:
            '200':
              description: Pet created
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          responses:
            '200':
              description: Expected response to a valid request
    """
        ),
    )
    def test_load_yaml(self, mock_yaml_load, mock_open_file):
        parser = OpenAPISpecificationParser(self.filepath)
        self.assertEqual(parser.api_data["info"]["title"], "Sample API")
        self.assertEqual(parser.api_data["info"]["version"], "1.0.0")
        self.assertEqual(len(parser.api_data["servers"]), 2)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch(
        "yaml.safe_load",
        return_value=yaml.safe_load(
            """
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0
    servers:
      - url: https://api.example.com
      - url: https://staging.api.example.com
    paths:
      /pets:
        get:
          summary: List all pets
          responses:
            '200':
              description: A paged array of pets
        post:
          summary: Create a pet
          responses:
            '200':
              description: Pet created
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          responses:
            '200':
              description: Expected response to a valid request
    """
        ),
    )
    def test_get_servers(self, mock_yaml_load, mock_open_file):
        parser = OpenAPISpecificationParser(self.filepath)
        servers = parser._get_servers()
        self.assertEqual(servers, ["https://api.example.com", "https://staging.api.example.com"])

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch(
        "yaml.safe_load",
        return_value=yaml.safe_load(
            """
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0
    servers:
      - url: https://api.example.com
      - url: https://staging.api.example.com
    paths:
      /pets:
        get:
          summary: List all pets
          responses:
            '200':
              description: A paged array of pets
        post:
          summary: Create a pet
          responses:
            '200':
              description: Pet created
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          responses:
            '200':
              description: Expected response to a valid request
    """
        ),
    )
    def test_get_paths(self, mock_yaml_load, mock_open_file):
        parser = OpenAPISpecificationParser(self.filepath)
        paths = parser.get_paths()
        expected_paths = {
            "/pets": {
                "get": {
                    "summary": "List all pets",
                    "responses": {"200": {"description": "A paged array of pets"}},
                },
                "post": {"summary": "Create a pet", "responses": {"200": {"description": "Pet created"}}},
            },
            "/pets/{petId}": {
                "get": {
                    "summary": "Info for a specific pet",
                    "responses": {"200": {"description": "Expected response to a valid request"}},
                }
            },
        }
        self.assertEqual(paths, expected_paths)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch(
        "yaml.safe_load",
        return_value=yaml.safe_load(
            """
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0
    servers:
      - url: https://api.example.com
      - url: https://staging.api.example.com
    paths:
      /pets:
        get:
          summary: List all pets
          responses:
            '200':
              description: A paged array of pets
        post:
          summary: Create a pet
          responses:
            '200':
              description: Pet created
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          responses:
            '200':
              description: Expected response to a valid request
    """
        ),
    )
    def test_get_operations(self, mock_yaml_load, mock_open_file):
        parser = OpenAPISpecificationParser(self.filepath)
        operations = parser._get_operations("/pets")
        expected_operations = {
            "get": {
                "summary": "List all pets",
                "responses": {"200": {"description": "A paged array of pets"}},
            },
            "post": {"summary": "Create a pet", "responses": {"200": {"description": "Pet created"}}},
        }
        self.assertEqual(operations, expected_operations)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch(
        "yaml.safe_load",
        return_value=yaml.safe_load(
            """
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0
    servers:
      - url: https://api.example.com
      - url: https://staging.api.example.com
    paths:
      /pets:
        get:
          summary: List all pets
          responses:
            '200':
              description: A paged array of pets
        post:
          summary: Create a pet
          responses:
            '200':
              description: Pet created
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          responses:
            '200':
              description: Expected response to a valid request
    """
        ),
    )
    def test_print_api_details(self, mock_yaml_load, mock_open_file):
        parser = OpenAPISpecificationParser(self.filepath)
        with patch("builtins.print") as mocked_print:
            parser._print_api_details()
            mocked_print.assert_any_call("API Title:", "Sample API")
            mocked_print.assert_any_call("API Version:", "1.0.0")
            mocked_print.assert_any_call("Servers:", ["https://api.example.com", "https://staging.api.example.com"])
            mocked_print.assert_any_call("\nAvailable Paths and Operations:")


if __name__ == "__main__":
    unittest.main()
