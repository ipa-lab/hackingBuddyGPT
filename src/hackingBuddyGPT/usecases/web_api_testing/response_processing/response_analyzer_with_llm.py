import json
import re
from typing import Any, Dict
from unittest.mock import MagicMock

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import (
    PenTestingInformation,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptPurpose,
)
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.utils import tool_message


class ResponseAnalyzerWithLLM:
    """
    A class to parse and analyze HTTP responses using an LLM for different purposes
    such as parsing, analysis, documentation, and reporting.

    Attributes:
        purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
    """

    def __init__(self, purpose: PromptPurpose = None, llm_handler: LLMHandler = None):
        """
        Initializes the ResponseAnalyzer with an optional purpose and an LLM instance.

        Args:
            purpose (PromptPurpose, optional): The purpose for analyzing the HTTP response. Default is None.
            llm_handler (LLMHandler): Handles the llm operations. Default is None.
            prompt_engineer(PromptEngineer): Handles the prompt operations. Default is None.
        """
        self.purpose = purpose
        self.llm_handler = llm_handler
        self.pentesting_information = PenTestingInformation()

    def set_purpose(self, purpose: PromptPurpose):
        """
        Sets the purpose for analyzing the HTTP response.

        Args:
            purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
        """
        self.purpose = purpose

    def print_results(self, results: Dict[str, str]):
        """
        Prints the LLM responses in a structured and readable format.

        Args:
            results (dict): The LLM responses to be printed.
        """
        for prompt, response in results.items():
            print(f"Prompt: {prompt}")
            print(f"Response: {response}")
            print("-" * 50)

    def analyze_response(self, raw_response: str, prompt_history: list) -> tuple[dict[str, Any], list]:
        """
        Parses the HTTP response, generates prompts for an LLM, and processes each step with the LLM.

        Args:
            raw_response (str): The raw HTTP response string to parse and analyze.

        Returns:
            dict: A dictionary with the final results after processing all steps through the LLM.
        """
        status_code, headers, body = self.parse_http_response(raw_response)
        full_response = f"Status Code: {status_code}\nHeaders: {json.dumps(headers, indent=4)}\nBody: {body}"

        # Start processing the analysis steps through the LLM
        llm_responses = []
        steps_dict = self.pentesting_information.analyse_steps(full_response)
        for steps in steps_dict.values():
            response = full_response  # Reset to the full response for each purpose
            for step in steps:
                prompt_history, response = self.process_step(step, prompt_history)
                llm_responses.append(response)
                print(f"Response:{response}")

        return llm_responses

    def parse_http_response(self, raw_response: str):
        """
        Parses the raw HTTP response string into its components: status line, headers, and body.

        Args:
            raw_response (str): The raw HTTP response string to parse.

        Returns:
            tuple: A tuple containing the status code (int), headers (dict), and body (str).
        """
        header_body_split = raw_response.split("\r\n\r\n", 1)
        header_lines = header_body_split[0].split("\n")
        body = header_body_split[1] if len(header_body_split) > 1 else ""
        status_line = header_lines[0].strip()

        match = re.match(r"HTTP/1\.1 (\d{3}) (.*)", status_line)
        status_code = int(match.group(1)) if match else None
        if body.__contains__("<html"):
            body = ""

        elif status_code in [500, 400, 404, 422]:
            body = body
        else:
            print(f"Body:{body}")
            if body != "" or body != "":
                body = json.loads(body)
            if isinstance(body, list) and len(body) > 1:
                body = body[0]

        headers = {
            key.strip(): value.strip()
            for key, value in (line.split(":", 1) for line in header_lines[1:] if ":" in line)
        }

        match = re.match(r"HTTP/1\.1 (\d{3}) (.*)", status_line)
        status_code = int(match.group(1)) if match else None

        return status_code, headers, body

    def process_step(self, step: str, prompt_history: list) -> tuple[list, str]:
        """
        Helper function to process each analysis step with the LLM.
        """
        # Log current step
        # print(f'Processing step: {step}')
        prompt_history.append({"role": "system", "content": step})

        # Call the LLM and handle the response
        response, completion = self.llm_handler.call_llm(prompt_history)
        message = completion.choices[0].message
        prompt_history.append(message)
        tool_call_id = message.tool_calls[0].id

        # Execute any tool call results and handle outputs
        try:
            result = response.execute()
        except Exception as e:
            result = f"Error executing tool call: {str(e)}"
        prompt_history.append(tool_message(str(result), tool_call_id))

        return prompt_history, result


if __name__ == "__main__":
    # Example HTTP response to parse
    raw_http_response = """HTTP/1.1 404 Not Found
    Date: Fri, 16 Aug 2024 10:01:19 GMT
    Content-Type: application/json; charset=utf-8
    Content-Length: 2
    Connection: keep-alive
    Report-To: {"group":"heroku-nel","max_age":3600,"endpoints":[{"url":"https://nel.heroku.com/reports?ts=1723802269&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&s=dkvm744qehjJmab8kgf%2BGuZA8g%2FCCIkfoYc1UdYuZMc%3D"}]}
    Reporting-Endpoints: heroku-nel=https://nel.heroku.com/reports?ts=1723802269&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&s=dkvm744qehjJmab8kgf%2BGuZA8g%2FCCIkfoYc1UdYuZMc%3D
    Nel: {"report_to":"heroku-nel","max_age":3600,"success_fraction":0.005,"failure_fraction":0.05,"response_headers":["Via"]}
    X-Powered-By: Express
    X-Ratelimit-Limit: 1000
    X-Ratelimit-Remaining: 999
    X-Ratelimit-Reset: 1723802321
    Vary: Origin, Accept-Encoding
    Access-Control-Allow-Credentials: true
    Cache-Control: max-age=43200
    Pragma: no-cache
    Expires: -1
    X-Content-Type-Options: nosniff
    Etag: W/"2-vyGp6PvFo4RvsFtPoIWeCReyIC8"
    Via: 1.1 vegur
    CF-Cache-Status: HIT
    Age: 210
    Server: cloudflare
    CF-RAY: 8b40951728d9c289-VIE
    alt-svc: h3=":443"; ma=86400

    {}"""
    llm_mock = MagicMock()
    capabilities = {
        "submit_http_method": HTTPRequest("https://jsonplaceholder.typicode.com"),
        "http_request": HTTPRequest("https://jsonplaceholder.typicode.com"),
    }

    # Initialize the ResponseAnalyzer with a specific purpose and an LLM instance
    response_analyzer = ResponseAnalyzerWithLLM(
        PromptPurpose.PARSING, llm_handler=LLMHandler(llm=llm_mock, capabilities=capabilities)
    )

    # Generate and process LLM prompts based on the HTTP response
    results = response_analyzer.analyze_response(raw_http_response)

    # Print the LLM processing results
    response_analyzer.print_results(results)
