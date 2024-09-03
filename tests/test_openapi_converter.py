import os
import unittest
from unittest.mock import mock_open, patch

from hackingBuddyGPT.usecases.web_api_testing.documentation.parsing.openapi_converter import (
    OpenAPISpecificationConverter,
)


class TestOpenAPISpecificationConverter(unittest.TestCase):
    def setUp(self):
        self.converter = OpenAPISpecificationConverter("base_directory")

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data="yaml_content")
    @patch("yaml.safe_load", return_value={"key": "value"})
    @patch("json.dump")
    def test_convert_file_yaml_to_json(self, mock_json_dump, mock_yaml_safe_load, mock_open_file, mock_makedirs):
        input_filepath = "input.yaml"
        output_directory = "json"
        input_type = "yaml"
        output_type = "json"
        expected_output_path = os.path.join("base_directory", output_directory, "input.json")

        result = self.converter.convert_file(input_filepath, output_directory, input_type, output_type)

        mock_open_file.assert_any_call(input_filepath, "r")
        mock_yaml_safe_load.assert_called_once()
        mock_open_file.assert_any_call(expected_output_path, "w")
        mock_json_dump.assert_called_once_with({"key": "value"}, mock_open_file(), indent=2)
        mock_makedirs.assert_called_once_with(os.path.join("base_directory", output_directory), exist_ok=True)
        self.assertEqual(result, expected_output_path)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    @patch("json.load", return_value={"key": "value"})
    @patch("yaml.dump")
    def test_convert_file_json_to_yaml(self, mock_yaml_dump, mock_json_load, mock_open_file, mock_makedirs):
        input_filepath = "input.json"
        output_directory = "yaml"
        input_type = "json"
        output_type = "yaml"
        expected_output_path = os.path.join("base_directory", output_directory, "input.yaml")

        result = self.converter.convert_file(input_filepath, output_directory, input_type, output_type)

        mock_open_file.assert_any_call(input_filepath, "r")
        mock_json_load.assert_called_once()
        mock_open_file.assert_any_call(expected_output_path, "w")
        mock_yaml_dump.assert_called_once_with(
            {"key": "value"}, mock_open_file(), allow_unicode=True, default_flow_style=False
        )
        mock_makedirs.assert_called_once_with(os.path.join("base_directory", output_directory), exist_ok=True)
        self.assertEqual(result, expected_output_path)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data="yaml_content")
    @patch("yaml.safe_load", side_effect=Exception("YAML error"))
    def test_convert_file_yaml_to_json_error(self, mock_yaml_safe_load, mock_open_file, mock_makedirs):
        input_filepath = "input.yaml"
        output_directory = "json"
        input_type = "yaml"
        output_type = "json"

        result = self.converter.convert_file(input_filepath, output_directory, input_type, output_type)

        mock_open_file.assert_any_call(input_filepath, "r")
        mock_yaml_safe_load.assert_called_once()
        mock_makedirs.assert_called_once_with(os.path.join("base_directory", output_directory), exist_ok=True)
        self.assertIsNone(result)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    @patch("json.load", side_effect=Exception("JSON error"))
    def test_convert_file_json_to_yaml_error(self, mock_json_load, mock_open_file, mock_makedirs):
        input_filepath = "input.json"
        output_directory = "yaml"
        input_type = "json"
        output_type = "yaml"

        result = self.converter.convert_file(input_filepath, output_directory, input_type, output_type)

        mock_open_file.assert_any_call(input_filepath, "r")
        mock_json_load.assert_called_once()
        mock_makedirs.assert_called_once_with(os.path.join("base_directory", output_directory), exist_ok=True)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
