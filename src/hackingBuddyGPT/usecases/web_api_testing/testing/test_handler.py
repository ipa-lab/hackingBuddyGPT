import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Tuple

import pydantic_core


class TestHandler(object):

    def __init__(self, llm_handler):
        self._llm_handler = llm_handler
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.test_path = os.path.join(current_path, "tests")
        self.filename = f"test{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        self.file = os.path.join(self.test_path, self.filename)

    def parse_test_case(self, note: str) -> Dict[str, Any]:
            """
            Parses a note containing a test case into a structured format.

            Args:
                note (str): The note string containing the test case information.

            Returns:
                Dict[str, Any]: The parsed test case in a structured format.
            """
            # Regular expressions to extract the method, endpoint, input, and expected output
            method_endpoint_pattern = re.compile(r"Test Case for (\w+) (\/\S+):")
            description_pattern = re.compile(r"Description: (.+)")
            input_data_pattern = re.compile(r"Input Data: (\{.*\})")
            expected_output_pattern = re.compile(r"Expected Output: (.+)")

            # Extract method and endpoint
            method_endpoint_match = method_endpoint_pattern.search(note)
            if method_endpoint_match:
                method, endpoint = method_endpoint_match.groups()
            else:
                raise ValueError("Method and endpoint not found in the note")

            # Extract description
            description_match = description_pattern.search(note)
            description = description_match.group(1) if description_match else "No description found"

            # Extract input data
            input_data_match = input_data_pattern.search(note)
            input_data = input_data_match.group(1) if input_data_match else "{}"

            # Extract expected output
            expected_output_match = expected_output_pattern.search(note)
            expected_output = expected_output_match.group(1) if expected_output_match else "No expected output found"

            # Construct the structured test case
            test_case = {
                "description": f"Test case for {method} {endpoint}",
                "input": input_data,
                "expected_output": expected_output
            }

            return test_case

    def generate_test_case(self, analysis: str, endpoint: str, method: str, prompt_history) -> Tuple[str, Dict[str, Any]]:
        """
        Generates a test case based on the provided analysis of the API response.

        Args:
            analysis (str): Analysis of the API response and its behavior.
            endpoint (str): The API endpoint being tested.
            method (str): The HTTP method to use in the test case.

        Returns:
            Tuple[str, Dict[str, Any]]: A description of the test case and the payload.
        """
        prompt_text = f"""
           Based on the following analysis of the API response, generate a detailed test case:

           Analysis: {analysis}

           Endpoint: {endpoint}
           HTTP Method: {method}

           The test case should include:
           - Description of the test.
           - Example input data in JSON format.
           - Expected result or assertion.

           Example Format:
           {{
               "description": "Test case for {method} {endpoint}",
               "input": {{}},
               "expected_output": {{}}
           }}
           """
        prompt_history.append({"role": "system", "content": prompt_text})

        response, completion = self._llm_handler.call_llm(prompt_history)
        message = completion.choices[0].message
        tool_call_id: str = message.tool_calls[0].id
        command: str = pydantic_core.to_json(response).decode()
        result: Any = response.execute()
        test_case = self.parse_test_case(result)
        # Extract the structured test case if possible
        try:
            test_case_dict = json.loads(test_case)
        except json.JSONDecodeError:
            raise ValueError("LLM-generated test case is not valid JSON")

        return test_case_dict["description"], test_case_dict

    def write_test_case_to_file(self, description: str, test_case: Dict[str, Any]) -> None:
        """
        Writes a generated test case to a specified file.

        Args:
            description (str): Description of the test case.
            test_case (Dict[str, Any]): The test case including input and expected output.
            output_file (str): The file path where the test case should be saved.
        """
        test_case_entry = {
            "description": description,
            "test_case": test_case
        }

        with open(self.file + ".json", "a") as f:
            f.write(json.dumps(test_case_entry, indent=2) + "\n\n")

        print((f"Test case written to {self.file}"))

    def write_pytest_case(self, description: str, test_case: Dict[str, Any]) -> None:
        """
        Writes a pytest-compatible test case to a Python file using LLM for code generation.

        Args:
            description (str): Description of the test case.
            test_case (Dict[str, Any]): The test case including input and expected output.
        """
        # Construct a prompt to guide the LLM in generating the test code.
        prompt = f"""
        You are an expert Python developer specializing in writing automated tests using pytest.
        Based on the following details, generate a pytest-compatible test function:

        Description: {description}

        Test Case:
        - Endpoint: {test_case['endpoint']}
        - HTTP Method: {test_case['method'].upper()}
        - Input Data: {json.dumps(test_case.get("input", {}), indent=4)}
        - Expected Status Code: {test_case['expected_output'].get('status_code', 200)}
        - Expected Response Body: {json.dumps(test_case['expected_output'].get('body', {}), indent=4)}

        The generated test function should:
        - Use the 'requests' library to make the HTTP request.
        - Include assertions for the status code and the response body.
        - Be properly formatted and ready to use with pytest.
        - Include a docstring with the test description.

        Example Format:
        ```
        import requests
        import pytest

        @pytest.mark.api
        def test_example():
            \"\"\"Description of the test.\"\"\"
            # Test implementation here
        ```
        """

        # Call the LLM to generate the test function.
        response = self._llm_handler.call_llm(prompt)
        test_function = response['choices'][0]['text']

        # Write the generated test function to a Python file.
        with open(self.file + ".py", "a") as f:
            f.write(test_function)

        print(f"Pytest case written to {self.file}.py")

    def generate_and_save_test_cases(self, analysis: str, endpoint: str, method: str, prompt_history) -> None:
        """
        Generates test cases based on the analysis and saves them as pytest-compatible tests.

        Args:
            analysis (str): Analysis of the API response.
            endpoint (str): The endpoint being tested.
            method (str): The HTTP method used for testing.
        """
        description, test_case = self.generate_test_case(analysis, endpoint, method, prompt_history)
        self.write_test_case_to_file(description, test_case)
        self.write_pytest_case(description, test_case)
