import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Tuple


class GenerationTestHandler:
    """
    A class responsible for parsing, generating, and saving structured API test cases,
    including generating pytest-compatible test functions using an LLM.

    Attributes:
        _llm_handler: Handler to communicate with a language model (LLM).
        test_path (str): Directory path for saving test case data.
        file (str): Path to the file for saving structured test case data.
        test_file (str): Path to the file for saving pytest test functions.
    """

    def __init__(self, llm_handler):
        """
        Initializes the TestHandler with paths for saving generated test case data.

        Args:
            llm_handler: LLM handler instance used for generating test logic from prompts.
        """
        self._llm_handler = llm_handler
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.test_path = os.path.join(current_path, "tests", f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        os.makedirs(self.test_path, exist_ok=True)

        self.file = os.path.join(self.test_path, "test_cases.txt")
        self.test_file = os.path.join(self.test_path, "python_test.py")

    def parse_test_case(self, note: str) -> Dict[str, Any]:
        """
        Parses a text note into a structured test case dictionary.

        Args:
            note (str): A human-readable note that describes the test case.

        Returns:
            dict: A structured test case with description, input, and expected output.
        """
        method_endpoint_pattern = re.compile(r"Test case for (\w+) (\/\S+):")
        description_pattern = re.compile(r"Description: (.+)")
        input_data_pattern = re.compile(r"Input Data: (\{.*\})")
        expected_output_pattern = re.compile(r"Expected Output: (.+)")

        method_endpoint_match = method_endpoint_pattern.search(note)
        if method_endpoint_match:
            method, endpoint = method_endpoint_match.groups()
        else:
            raise ValueError("Method and endpoint not found in the note")

        description = description_pattern.search(note).group(1) if description_pattern.search(
            note) else "No description found"
        input_data = input_data_pattern.search(note).group(1) if input_data_pattern.search(note) else "{}"
        expected_output = expected_output_pattern.search(note).group(1) if expected_output_pattern.search(
            note) else "No expected output found"

        return {
            "description": f"Test case for {method} {endpoint}",
            "input": input_data,
            "expected_output": expected_output
        }

    def generate_test_case(self, analysis: str, endpoint: str, method: str, body:str, status_code: Any, prompt_history) -> Tuple[
        str, Dict[str, Any], list]:
        """
        Uses LLM to generate a test case dictionary from analysis and test metadata.

        Args:
            analysis (str): Textual analysis of API behavior.
            endpoint (str): API endpoint.
            method (str): HTTP method used.
            status_code (Any): Expected HTTP status code.
            prompt_history (list): History of prompts exchanged with the LLM.

        Returns:
            tuple: Test case description, test case dictionary, and updated prompt history.
        """
        prompt_text = f"""Based on the following analysis of the API response, generate a detailed test case:

           Analysis: {analysis}

           Endpoint: {endpoint}
           HTTP Method: {method}

           The test case should include:
           - Description of the test.
           - Example input data in JSON format.
           - Expected result or assertion based on method and endpoint call.

           return a PythonTestCase object that should look like this :
            Format:
           {{
               "description": "Test case for {method} {endpoint}",
               "input": {body},
               "expected_output": {{"expected_body": body, "expected_status_code": status_code}}
           }},
        """
        prompt_history.append({"role": "system", "content": prompt_text})
        response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt_history,
                                                                                         capability="python_test_case")
        test_case = response.execute()

        test_case["method"] = method
        test_case["endpoint"] = endpoint

        return test_case["description"], test_case, prompt_history

    def write_test_case_to_file(self, description: str, test_case: Dict[str, Any]) -> None:
        """
        Saves a structured test case to a text file.

        Args:
            description (str): Description of the test.
            test_case (dict): Test case dictionary.
        """
        entry = {
            "description": description,
            "test_case": test_case
        }
        with open(self.file, "a") as f:
            f.write(json.dumps(entry, indent=2) + "\n\n")
        print(f"Test case written to {self.file}")

    def write_pytest_case(self, description: str, test_case: Dict[str, Any], prompt_history) -> list:
        """
        Uses LLM to generate a pytest-compatible test function and saves it to a `.py` file.

        Args:
            description (str): Description of the test case.
            test_case (dict): Test case dictionary.
            prompt_history (list): Prompt history for LLM context.

        Returns:
            list: Updated prompt history.
        """
        prompt = f"""
        As a testing expert, you are tasked with creating pytest-compatible test functions using the Python 'requests' library (also import it).

        Test Details:
         - Description: {description}
        - Endpoint: {test_case['endpoint']}
        - Method: {test_case['method'].upper()}
        - Input: {json.dumps(test_case.get("input", {}), indent=4)}
        - Expected Status: {test_case['expected_output'].get('expected_status_code')}
        - Expected Body: {test_case['expected_output'].get('expected_body', {})}

        Instructions:
        Write a syntactically and semantically correct pytest function that:
        - Includes a docstring explaining the purpose of the test.
        - Sends the appropriate HTTP request to the specified endpoint.
        - Asserts the correctness of both the response status code and the response body.

        Test Function Name:
        Use the description to create a meaningful and relevant test function name, following Python's naming conventions for functions.

        Example:
        If the description is "Test for successful login", the function name could be 'test_successful_login'.

        Code Example:
        def test_function_name():
            \"""Docstring describing the test purpose.\"""
            response = requests.METHOD('http://example.com/api/endpoint', json={{"key": "value"}})
            assert response.status_code == 200
            assert response.json() == {{"expected": "output"}}

        Replace 'METHOD', 'http://example.com/api/endpoint', and other placeholders with actual data based on the test details provided."""

        prompt_history.append({"role": "system", "content": prompt})
        response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt_history, "record_note")
        result = response.execute()

        test_function = self.extract_pytest_from_string(result)
        if test_function:
            with open(self.test_file, "a") as f:
                f.write(test_function)
            print(f"Pytest case written to {self.test_file}")

        return prompt_history

    def extract_pytest_from_string(self, text: str) -> str:
        """
        Extracts the first Python function definition from a string.

        Args:
            text (str): Raw string potentially containing Python code.

        Returns:
            str: Extracted function block, or None if not found.
        """
        func_start = text.find("import ")
        if func_start == -1:
            func_start = text.find("def ")
            if func_start == -1:
                return None

        func_end = text.find("import ", func_start + 1)
        if func_end == -1:
            func_end = len(text)

        return text[func_start:func_end]

    def generate_test_cases(self, analysis: str, endpoint: str, method: str, body:str,  status_code: Any, prompt_history) -> list:
        """
        Generates and stores both JSON and Python test cases based on analysis.

        Args:
            analysis (str): Analysis summary of the API behavior.
            endpoint (str): API endpoint.
            method (str): HTTP method.
            status_code (Any): Expected status code.
            prompt_history (list): Prompt history.

        Returns:
            list: Updated prompt history.
        """
        description, test_case, prompt_history = self.generate_test_case(analysis, endpoint, method, body, status_code,
                                                                         prompt_history)
        self.write_test_case_to_file(description, test_case)
        prompt_history = self.write_pytest_case(description, test_case, prompt_history)
        return prompt_history

    def get_status_code(self, description: str) -> int:
        """
        Extracts the first HTTP status code (3-digit integer) from a description string.

        Args:
            description (str): A string potentially containing a status code.

        Returns:
            int: The extracted status code.

        Raises:
            ValueError: If no 3-digit status code is found.
        """
        match = re.search(r"\b(\d{3})\b", description)
        if match:
            return int(match.group(1))
        raise ValueError("No valid status code found in the description.")

