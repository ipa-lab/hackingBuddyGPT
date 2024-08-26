import json
import re

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptPurpose


class ResponseAnalyzer(object):
    """
    A class to parse and analyze HTTP responses based on different purposes, such as
    authentication/authorization checks and input validation.

    Attributes:
        purpose (PromptPurpose): The specific purpose for analyzing the HTTP response. It determines
                                 which analysis method will be applied.
    """

    def __init__(self, purpose=None):
        """
        Initializes the ResponseAnalyzer with an optional purpose.

        Args:
            purpose (PromptPurpose, optional): The purpose for analyzing the HTTP response. Default is None.
        """
        self.purpose = purpose

    def set_purpose(self, purpose):
        """
        Sets the purpose for analyzing the HTTP response.

        Args:
            purpose (PromptPurpose): The specific purpose for analyzing the HTTP response.
        """
        self.purpose = purpose

    def parse_http_response(self, raw_response):
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
        #print(f'Body:{body}')
        if body != {} and bool(body and not body.isspace()):
            body = json.loads(body)[0]
        else:
            body = "Empty"

        status_line = header_lines[0].strip()
        headers = {key.strip(): value.strip() for key, value in
                   (line.split(":", 1) for line in header_lines[1:] if ':' in line)}

        match = re.match(r"HTTP/1\.1 (\d{3}) (.*)", status_line)
        status_code = int(match.group(1)) if match else None

        return status_code, headers, body

    def analyze_response(self, raw_response):
        """
        Parses the HTTP response and analyzes it based on the set purpose.

        Args:
            raw_response (str): The raw HTTP response string to parse and analyze.

        Returns:
            dict: The analysis results based on the purpose.
        """
        status_code, headers, body = self.parse_http_response(raw_response)
        return self.analyze_parsed_response(status_code, headers, body)

    def analyze_parsed_response(self, status_code, headers, body):
        """
        Analyzes the parsed HTTP response based on the purpose, invoking the appropriate method.

        Args:
            status_code (int): The HTTP status code.
            headers (dict): The HTTP headers.
            body (str): The HTTP response body.

        Returns:
            dict: The analysis results based on the purpose.
        """
        analysis_methods = {
            PromptPurpose.AUTHENTICATION_AUTHORIZATION: self.analyze_authentication_authorization(status_code, headers,
                                                                                                  body),
            PromptPurpose.INPUT_VALIDATION: self.analyze_input_validation(status_code, headers, body),
        }
        return analysis_methods.get(self.purpose)

    def analyze_authentication_authorization(self, status_code, headers, body):
        """
        Analyzes the HTTP response with a focus on authentication and authorization.

        Args:
            status_code (int): The HTTP status code.
            headers (dict): The HTTP headers.
            body (str): The HTTP response body.

        Returns:
            dict: The analysis results focused on authentication and authorization.
        """
        analysis = {
            'status_code': status_code,
            'authentication_status': "Authenticated" if status_code == 200 else
            "Not Authenticated or Not Authorized" if status_code in [401, 403] else "Unknown",
            'auth_headers_present': any(
                header in headers for header in ['Authorization', 'Set-Cookie', 'WWW-Authenticate']),
            'rate_limiting': {
                'X-Ratelimit-Limit': headers.get('X-Ratelimit-Limit'),
                'X-Ratelimit-Remaining': headers.get('X-Ratelimit-Remaining'),
                'X-Ratelimit-Reset': headers.get('X-Ratelimit-Reset'),
            },
            'content_body': "Empty" if body ==  {} else body,
        }
        return analysis

    def analyze_input_validation(self, status_code, headers, body):
        """
        Analyzes the HTTP response with a focus on input validation.

        Args:
            status_code (int): The HTTP status code.
            headers (dict): The HTTP headers.
            body (str): The HTTP response body.

        Returns:
            dict: The analysis results focused on input validation.
        """
        analysis = {
            'status_code': status_code,
            'response_body': "Empty" if body == {}  else body,
            'is_valid_response': self.is_valid_input_response(status_code, body),
            'security_headers_present': any(key in headers for key in ["X-Content-Type-Options", "X-Ratelimit-Limit"]),
        }
        return analysis

    def is_valid_input_response(self, status_code, body):
        """
        Determines if the HTTP response is valid based on the status code and body content.

        Args:
            status_code (int): The HTTP status code.
            body (str): The HTTP response body.

        Returns:
            str: The validity status ("Valid", "Invalid", "Error", or "Unexpected").
        """
        if status_code == 200:
            return "Valid"
        elif status_code == 400:
            return "Invalid"
        elif status_code in [401, 403, 404, 500]:
            return "Error"
        else:
            return "Unexpected"

    def document_findings(self, status_code, headers, body, expected_behavior, actual_behavior):
        """
        Documents the findings from the analysis, comparing expected and actual behavior.

        Args:
            status_code (int): The HTTP status code.
            headers (dict): The HTTP headers.
            body (str): The HTTP response body.
            expected_behavior (str): The expected behavior of the API.
            actual_behavior (str): The actual behavior observed.

        Returns:
            dict: A dictionary containing the documented findings.
        """
        document = {
            "Status Code": status_code,
            "Headers": headers,
            "Response Body": body.strip(),
            "Expected Behavior": expected_behavior,
            "Actual Behavior": actual_behavior,
        }
        print("Documenting Findings:")
        print(json.dumps(document, indent=4))
        print("-" * 50)
        return document

    def report_issues(self, document):
        """
        Reports any discrepancies found during analysis, suggesting improvements where necessary.

        Args:
            document (dict): The documented findings to be reported.
        """
        print("Reporting Issues:")
        if document["Expected Behavior"] != document["Actual Behavior"]:
            print("Issue Found:")
            print(f"Expected: {document['Expected Behavior']}")
            print(f"Actual: {document['Actual Behavior']}")
            print("Suggestion: Improve input validation, clearer error messages, or enhanced security measures.")
        else:
            print("No issues found in this test case.")
        print("-" * 50)

    def print_analysis(self, analysis):
        """
        Prints the analysis results in a structured and readable format.

        Args:
            analysis (dict): The analysis results to be printed.
        """
        fields_to_print = {
            "HTTP Status Code": analysis.get("status_code"),
            "Response Body": analysis.get("response_body"),
            "Content Body": analysis.get("content_body"),
            "Valid Response": analysis.get("is_valid_response"),
            "Authentication Status": analysis.get("authentication_status"),
            "Security Headers Present": "Yes" if analysis.get("security_headers_present") else "No",
        }
        analysis_str="\n"

        for label, value in fields_to_print.items():
            if label == "Content Body":
                if value is not None:
                    analysis_str += f"{label}: {fields_to_print['Content Body']}"
            else:
                if value is not None:
                    analysis_str += f"{label}: {value}\n"

        if "rate_limiting" in analysis:
            analysis_str += f"Rate Limiting Information:\n"

            for key, value in analysis["rate_limiting"].items():
                analysis_str += f"  {key}: {value}\n"

        analysis_str += "-" * 50
        return analysis_str

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
    respons_analyzer = ResponseAnalyzer()
    respons_analyzer.purpose = PromptPurpose.AUTHENTICATION_AUTHORIZATION
    # Parse and analyze the HTTP response
    analysis = respons_analyzer.analyze_response(raw_http_response)

    # Print the analysis results
    respons_analyzer.print_analysis(analysis)
    respons_analyzer = ResponseAnalyzer()
    respons_analyzer.purpose = PromptPurpose.INPUT_VALIDATION
    # Parse and analyze the HTTP response
    analysis = respons_analyzer.analyze_response(raw_http_response)

    # Print the analysis results
    print(respons_analyzer.print_analysis(analysis))
