import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Tuple


class TestHandler(object):

    def __init__(self, llm_handler):
        self._llm_handler = llm_handler
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.test_path = os.path.join(current_path, "tests", f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        os.makedirs(self.test_path, exist_ok=True)

        self.file = os.path.join(self.test_path, "test_cases.txt")
        self.test_file = os.path.join(self.test_path, "python_test.py")

    def parse_test_case(self, note: str) -> Dict[str, Any]:
        """
        Parses a note containing a test case into a structured format.

        Args:
            note (str): The note string containing the test case information.

        Returns:
            Dict[str, Any]: The parsed test case in a structured format.
        """
        # Regular expressions to extract the method, endpoint, input, and expected output
        method_endpoint_pattern = re.compile(r"Test case for (\w+) (\/\S+):")
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

    def generate_test_case(self, analysis: str, endpoint: str, method: str, status_code: Any, prompt_history) -> Any:
        """
        Generates a test case based on the provided analysis of the API response.

        Args:
            analysis (str): Analysis of the API response and its behavior.
            endpoint (str): The API endpoint being tested.
            method (str): The HTTP method to use in the test case.

        Returns:
            Tuple[str, Dict[str, Any]]: A description of the test case and the payload.
        """
        print(f'Analysis:{analysis}')
        prompt_text = f"""
           Based on the following analysis of the API response, generate a detailed test case:

           Analysis: {analysis}

           Endpoint: {endpoint}
           HTTP Method: {method}

           The test case should include:
           - Description of the test.
           - Example input data in JSON format.
           - Expected result or assertion based on method and endpoint call.

           Example Format:
           {{
               "description": "Test case for {method} {endpoint}",
               "input": {{}},
               "expected_output": {{"expected_body": body, "expected_status_code": status_code}}
           }}
           
           return a PythonTestCase object
           """
        prompt_history.append({"role": "system", "content": prompt_text})
        response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt_history,
                                                                                         capability="python_test_case")
        test_case: Any = response.execute()
        print(f'RESULT: {test_case}')
        test_case["method"] = method
        test_case["endpoint"] = endpoint

        # test_case = self.parse_test_case(result)
        # Extract the structured test case if possible
        '''try:
            test_case_dict = json.loads(test_case)
        except json.JSONDecodeError:
            raise ValueError("LLM-generated test case is not valid JSON")'''

        return test_case["description"], test_case, prompt_history

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

        with open(self.file, "a") as f:
            f.write(json.dumps(test_case_entry, indent=2) + "\n\n")

        print((f"Test case written to {self.file}"))

    def write_pytest_case(self, description: str, test_case: Dict[str, Any], prompt_history) -> None:
        """
        Writes a pytest-compatible test case to a Python file using LLM for code generation.

        Args:
            description (str): Description of the test case.
            test_case (Dict[str, Any]): The test case including input and expected output.
        """
        # Construct a prompt to guide the LLM in generating the test code.

        prompt = f"""
            You are an expert in writing pytest-compatible test functions.
            
            Details:
            - Description: {description}
            - Endpoint: {test_case['endpoint']}
            - Method: {test_case['method'].upper()}
            - Input: {json.dumps(test_case.get("input", {}), indent=4)}
            - Expected Status: {test_case['expected_output'].get('expected_status_code')}
            - Expected Body: {test_case['expected_output'].get('expected_body', {})}
            
            Write a pytest function that:
            - Uses 'requests' for the HTTP request.
            - Asserts the status code and response body.
            - Is well-formatted with a docstring for the description.
            Format should be like this: 
            ```def test_get_change_password_unauthorized():
            '''Test case for GET /user/change-password'''
                 url = 'http://localhost:3000/user/change-password'
                 response = requests.get(url)
                assert response.status_code == 401
                assert response.text == 'Password cannot be empty.'
            ```
            """

        prompt_history.append({"role": "system", "content": prompt})

        # Call the LLM to generate the test function.
        response, completion = self._llm_handler.execute_prompt_with_specific_capability(prompt_history, "record_note")
        result = response.execute()
        print(f'RESULT: {result}')

        test_function = self.extract_pytest_from_string(result)
        print(f'test_function: {test_function}')


        # Write the generated test function to a Python file.
        if test_function != None:
            with open(self.test_file, "a") as f:
            
                f.write(test_function)

            print(f"Pytest case written to {self.file}.py")
        return prompt_history

    def extract_pytest_from_string(self, text):
        """
        Extracts a Python test case or any function from a given text string, starting with the 'def' keyword.

        :param text: The string containing potential Python function definitions.
        :return: The extracted Python function as a string, or None if no function is found.
        """
        # Define the function start keyword
        func_start_keyword = "import "

        # Find the start of any Python function definition
        start_idx = text.find(func_start_keyword)
        if start_idx == -1:
            start_idx = text.find("def ")
            if start_idx == -1:
                return None

        # Assume the function ends at the next 'def ' or at the end of the text
        end_idx = text.find(func_start_keyword, start_idx + 1)
        if end_idx == -1:
            end_idx = len(text)

        # Extract the function
        function_block = text[start_idx:end_idx]
        return function_block

    def generate_test_cases(self, analysis: str, endpoint: str, method: str, status_code: Any, prompt_history) -> Any:
        """
        Generates test cases based on the analysis and saves them as pytest-compatible tests.

        Args:
            analysis (str): Analysis of the API response.
            endpoint (str): The endpoint being tested.
            method (str): The HTTP method used for testing.
        """
        description, test_case, prompt_history = self.generate_test_case(analysis, endpoint, method, status_code, prompt_history)
        self.write_test_case_to_file(description, test_case)
        prompt_history = self.write_pytest_case(description, test_case, prompt_history)
        return  prompt_history

    def get_status_code(self, description: str) -> int:
        """
        Extracts the status code from a textual description of an expected response.

        Args:
            description (str): The description containing the status code.

        Returns:
            int: The extracted status code.

        Raises:
            ValueError: If no valid status code is found in the description.
        """
        # Regular expression to find HTTP status codes (3-digit numbers)
        status_code_pattern = re.compile(r"\b(\d{3})\b")
        match = status_code_pattern.search(description)

        if match:
            return int(match.group(1))
        else:
            raise ValueError("No valid status code found in the description.")
