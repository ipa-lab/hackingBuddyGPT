import json
import re
from typing import Dict, List, Tuple, Any
from unittest.mock import MagicMock
import openai
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptPurpose
from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler
from hackingBuddyGPT.utils import tool_message
from transformers import pipeline


class ResponseAnalyzerWithLLM:
    """
    A class to parse and analyze HTTP responses using an LLM for different purposes
    such as parsing, analysis, documentation, and reporting.

    Attributes:
        purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
    """

    def __init__(self, purpose: PromptPurpose = None, llm_handler: LLMHandler=None):
        """
        Initializes the ResponseAnalyzer with an optional purpose and an LLM instance.

        Args:
            purpose (PromptPurpose, optional): The purpose for analyzing the HTTP response. Default is None.
            llm_handler (LLMHandler): Handles the . Default is None.
        """
        self.purpose = purpose
        self.llm_handler = llm_handler

    def set_purpose(self, purpose: PromptPurpose):
        """
        Sets the purpose for analyzing the HTTP response.

        Args:
            purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
        """
        self.purpose = purpose

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
        print(f'Body:{body}')
        if body.__contains__("<html"):
            body = ""
        else:
            body = json.loads(body)
            if isinstance(body, list) and len(body) > 1:
                body = body[0]

        status_line = header_lines[0].strip()
        headers = {key.strip(): value.strip() for key, value in
                   (line.split(":", 1) for line in header_lines[1:] if ':' in line)}

        match = re.match(r"HTTP/1\.1 (\d{3}) (.*)", status_line)
        status_code = int(match.group(1)) if match else None

        return status_code, headers, body

    def analyze_response(self, raw_response: str, prompt_history:list) -> tuple[dict[str, Any], list]:
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
        llm_responses = {}
        for purpose, steps in self.analyse_steps(full_response).items():
            analyse_step = purpose
            if purpose == analyse_step:
                response = full_response  # Start with the raw response
                for step in steps:
                    # Send the current step as a prompt to the LLM and capture the response

                    try:
                        prompt_history.append({"role": "system", "content": step})
                        print(f'Step:{step}')
                        response, completion = self.llm_handler.call_llm(prompt_history)
                    except openai.BadRequestError:
                        # Check if there are more than 10 elements in the list
                        if len(prompt_history) > 10:
                            # Remove 10 if even, 11 if odd, directly using slicing
                            prompt_history = prompt_history[10 + len(prompt_history) % 2:]
                        #prompt_history = self.summarize_prompt(prompt_history, step)
                        response, completion = self.llm_handler.call_llm(prompt_history)


                    message = completion.choices[0].message
                    prompt_history.append(message)
                    tool_call_id = message.tool_calls[0].id
                    result = response.execute()
                    prompt_history.append(tool_message(str(result), tool_call_id))
                    llm_responses[step] = response

        return llm_responses, prompt_history

    def analyse_steps(self, response: str = "") -> Dict[PromptPurpose, List[str]]:
        """
        Provides prompts for analysis based on the provided response for various purposes using an LLM.

        Args:
            response (str, optional): The HTTP response to analyze. Default is an empty string.

        Returns:
            dict: A dictionary where each key is a PromptPurpose and each value is a list of prompts.
        """
        return {
            PromptPurpose.PARSING: [ f"""  Please parse this response and extract the following details in JSON format: {{
                    "Status Code": "<status code>",
                    "Reason Phrase": "<reason phrase>",
                    "Headers": <headers as JSON>,
                    "Response Body": <body as JSON>
                    from this response: {response}
              
                }}"""

        ],
            PromptPurpose.ANALYSIS: [
                f'Given the following parsed HTTP response:\n{response}\n'
                'Please analyze this response to determine:\n'
                '1. Whether the status code is appropriate for this type of request.\n'
                '2. If the headers indicate proper security and rate-limiting practices.\n'
                '3. Whether the response body is correctly handled.'
            ],
            PromptPurpose.DOCUMENTATION: [
                f'Based on the analysis provided, document the findings of this API response validation:\n{response}'
            ],
            PromptPurpose.REPORTING: [
                f'Based on the documented findings : {response}. Suggest any improvements or issues that should be reported to the API developers.'
            ]
        }

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

    def summarize_prompt(self, prompt_history, text):

        # Load summarization pipeline
        summarizer = pipeline("summarization")

        text = "Your long text goes here. It can be multiple paragraphs describing an event, a concept, or an argument."
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)
        print(summary[0]['summary_text'])
        return summary


if __name__ == '__main__':
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
        "submit_http_method": HTTPRequest('https://jsonplaceholder.typicode.com'),
        "http_request": HTTPRequest('https://jsonplaceholder.typicode.com'),
    }

    # Initialize the ResponseAnalyzer with a specific purpose and an LLM instance
    response_analyzer = ResponseAnalyzerWithLLM(PromptPurpose.PARSING, llm_handler=LLMHandler(llm=llm_mock, capabilities=capabilities))

    # Generate and process LLM prompts based on the HTTP response
    results = response_analyzer.analyze_response(raw_http_response)

    # Print the LLM processing results
    response_analyzer.print_results(results)