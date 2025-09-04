import json
import re
from typing import Any, Dict
from unittest.mock import MagicMock

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.utils.prompt_generation.information import (
    PenTestingInformation,
)
from hackingBuddyGPT.utils.prompt_generation.information import (
    PromptPurpose,
)
from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler
from hackingBuddyGPT.utils import tool_message


class ResponseAnalyzerWithLLM:
    """
    A class to parse and analyze HTTP responses using an LLM for different purposes
    such as parsing, analysis, documentation, and reporting.

    Attributes:
        purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
    """

    def __init__(self, purpose: PromptPurpose = None, llm_handler: LLMHandler = None,
                 pentesting_info: PenTestingInformation = None, capacity: Any = None, prompt_helper: Any = None):
        """
        Initializes the ResponseAnalyzer with an optional purpose and an LLM instance.

        Args:
            purpose (PromptPurpose, optional): The purpose for analyzing the HTTP response. Default is None.
            llm_handler (LLMHandler): Handles the llm operations. Default is None.
            prompt_engineer(PromptEngineer): Handles the prompt operations. Default is None.
        """
        self.purpose = purpose
        self.llm_handler = llm_handler
        self.pentesting_information = pentesting_info
        self.capacity = capacity
        self.prompt_helper = prompt_helper
        self.token = ""

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

    def analyze_response(self, raw_response: str, prompt_history: list, analysis_context: Any) -> tuple[list[str], Any]:
        """
        Parses the HTTP response, generates prompts for an LLM, and processes each step with the LLM.

        Args:
            raw_response (str): The raw HTTP response string to parse and analyze.

        Returns:
            dict: A dictionary with the final results after processing all steps through the LLM.
        """

        # Start processing the analysis steps through the LLM
        llm_responses = []


        steps = analysis_context.get("steps")
        if len(steps) > 1:  # multisptep test case
            for step in steps:
                if step != steps[0]:

                    current_step = step.get("step")
                    prompt_history, raw_response = self.process_step(current_step, prompt_history, "http_request")
                test_case_responses, status_code = self.analyse_response(raw_response, step, prompt_history)
                llm_responses = llm_responses + test_case_responses
        else:
            llm_responses, status_code = self.analyse_response(raw_response, steps[0], prompt_history)

        return llm_responses, status_code

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
        if body == "":
            for line in header_lines:
                if line.startswith("{") or line.startswith("["):
                    body = line

        status_line = header_lines[0].strip()

        match = re.search(r"^HTTP/\d\.\d\s+(\d+)\s+(.*)", raw_response, re.MULTILINE)
        if match:
            status_code = match.group(1)
        else:
            status_code = None
        if body.__contains__("<!DOCTYPE"):
            body = ""

        elif status_code in ["500", "400", "404", "422"]:
            body = body
        else:

            if body.__contains__("<html>"):
                body = ""
            elif body.startswith("["):
                body = json.loads(body)
                print(f'"body:{body}')
            elif body.__contains__("{") and (body != '' or body != ""):
                if not  body.lower().__contains__("png") :
                    body = json.loads(body)
                    if "token" in body:

                        self.prompt_helper.current_user["token"] = body["token"]
                        self.token = body["token"]
                        for account in self.prompt_helper.accounts:
                                if account.get("x") == self.prompt_helper.current_user.get("x"):
                                    if  "token" not in account.keys():
                                        account["token"] = self.token
                                    else:
                                        if account["token"] != self.token:
                                            account["token"] = self.token
                                    print(f'token:{self.token}')
                                    print(f"accoun:{account}")
                    if any (value in body.values() for value in self.prompt_helper.current_user.values()):
                        if "id" in body:
                            for account in self.prompt_helper.accounts:
                                if account.get("x") == self.prompt_helper.current_user.get(
                                        "x") and "id" not in account.keys():
                                    account["id"] = body["id"]


                    #self.replace_account()
            elif isinstance(body, list) and len(body) > 1:
                body = body[0]
                if self.prompt_helper.current_user in body:
                    self.prompt_helper.current_user["id"] = self.get_id_from_user(body)
                    if self.prompt_helper.current_user not in self.prompt_helper.accounts:
                        self.prompt_helper.accounts.append(self.prompt_helper.current_user)
            else:
                if self.prompt_helper.current_user not in self.prompt_helper.accounts:
                    self.prompt_helper.accounts.append(self.prompt_helper.current_user)


        headers = {
            key.strip(): value.strip()
            for key, value in (line.split(":", 1) for line in header_lines[1:] if ":" in line)
        }

        if isinstance(body, str) and body.startswith(" <!doctype html>") and body.endswith("</html>"):
            body = ""

        return status_code, headers, body

    def get_id_from_user(self, body) -> str:
        id = body.split("id")[1].split(",")[0]
        return id


    def process_step(self, step: str, prompt_history: list, capability:str) -> tuple[list, str]:
        """
        Helper function to process each analysis step with the LLM.
        """
        # Log current step
        prompt_history.append({"role": "system", "content": step + "Stay within the output limit."})

        # Call the LLM and handle the response
        response, completion = self.llm_handler.execute_prompt_with_specific_capability(prompt_history, capability)
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id

        msg = {"role": message.role, "content": message.content, "tool_calls": message.tool_calls}
        prompt_history.append(msg)

        # Execute any tool call results and handle outputs
        try:
            result = response.execute()
        except Exception as e:
            result = f"Error executing tool call: {str(e)}"
        prompt_history.append(tool_message(str(result), tool_call_id))


        return prompt_history, result

    def analyse_response(self, raw_response, step, prompt_history):
        llm_responses = []

        status_code, additional_analysis_context, full_response= self.get_addition_context(raw_response, step)

        expected_responses = step.get("expected_response_code")


        if step.get("purpose") == PromptPurpose.SETUP:
            _, additional_analysis_context, full_response = self.do_setup(status_code, step,  additional_analysis_context, full_response, prompt_history)

        if not any(str(status_code) in response for response in expected_responses):
            additional_analysis_context += step.get("conditions").get("if_unsuccessful")
        else:
            additional_analysis_context += step.get("conditions").get("if_successful")

        llm_responses.append(full_response)
        if step.get("purpose") != PromptPurpose.SETUP:
            for purpose in self.pentesting_information.analysis_step_list:
                analysis_step = self.pentesting_information.get_analysis_step(purpose, full_response,
                                                                          additional_analysis_context)
                prompt_history, response = self.process_step(analysis_step, prompt_history, "record_note")
                llm_responses.append(response)
                full_response = response  # make it iterative

        return llm_responses, status_code

    def get_addition_context(self, raw_response: str, step: dict) :
        # Parse response
        status_code, headers, body = self.parse_http_response(raw_response)

        full_response = f"Status Code: {status_code}\nHeaders: {json.dumps(headers, indent=4)}\nBody: {body}"
        expected_responses = step.get("expected_response_code")
        security = step.get("security")
        additional_analysis_context = f"\n Ensure that the status code is one of the expected responses: '{expected_responses}\n Also ensure that the following security requirements have been met: {security}"
        return   status_code, additional_analysis_context, full_response

    def do_setup(self, status_code, step, additional_analysis_context, full_response, prompt_history):
        counter = 0
        if not any(str(status_code) in response for response in step.get("expected_response_code")):
            add_info = "Unsuccessful. Try a different input for the schema."
            while not any(str(status_code) in response for response in step.get("expected_response_code")):
                prompt_history, response = self.process_step(step.get("step") + add_info, prompt_history, "http_request")
                status_code, additional_analysis_context, full_response = self.get_addition_context(response, step)
                counter += 1

                if counter == 5:
                    full_response += "Unsuccessful:" + step.get("conditions").get("if_unsuccessful")
                    break



        return status_code, additional_analysis_context, full_response

    def replace_account(self):
        # Now let's replace the existing account if it exists, otherwise add it
        replaced = False
        for i, account in enumerate(self.prompt_helper.accounts):
            # Compare the 'id' (or any unique field) to find the matching account
            if account.get("x") == self.prompt_helper.current_user.get("x"):
                self.prompt_helper.accounts[i] = self.prompt_helper.current_user
                replaced = True
                break

        # If we did not replace any existing account, append this as a new account
        if not replaced:
            self.prompt_helper.accounts.append(self.prompt_helper.current_user)



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
