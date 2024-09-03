import unittest
from unittest.mock import patch

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptPurpose,
)
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer import (
    ResponseAnalyzer,
)


class TestResponseAnalyzer(unittest.TestCase):
    def setUp(self):
        # Example HTTP response to use in tests
        self.raw_http_response = """HTTP/1.1 404 Not Found
        Date: Fri, 16 Aug 2024 10:01:19 GMT
        Content-Type: application/json; charset=utf-8
        Content-Length: 2
        Connection: keep-alive
        Report-To: {"group":"heroku-nel","max_age":3600,"endpoints":[{"url":"https://nel.heroku.com/reports?ts=1723802269&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&s=dkvm744qehjJmab8kgf%2BGuZA8g%2FCCIkfoYc1UdYuZMc%3D"}]}
        X-Powered-By: Express
        X-Ratelimit-Limit: 1000
        X-Ratelimit-Remaining: 999
        X-Ratelimit-Reset: 1723802321
        Cache-Control: max-age=43200
        Server: cloudflare

        {}"""

    def test_parse_http_response(self):
        analyzer = ResponseAnalyzer()
        status_code, headers, body = analyzer.parse_http_response(self.raw_http_response)

        self.assertEqual(status_code, 404)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(body, "Empty")

    def test_analyze_authentication_authorization(self):
        analyzer = ResponseAnalyzer(PromptPurpose.AUTHENTICATION_AUTHORIZATION)
        analysis = analyzer.analyze_response(self.raw_http_response)

        self.assertEqual(analysis["status_code"], 404)
        self.assertEqual(analysis["authentication_status"], "Unknown")
        self.assertTrue(analysis["content_body"], "Empty")
        self.assertIn("X-Ratelimit-Limit", analysis["rate_limiting"])

    def test_analyze_input_validation(self):
        analyzer = ResponseAnalyzer(PromptPurpose.INPUT_VALIDATION)
        analysis = analyzer.analyze_response(self.raw_http_response)

        self.assertEqual(analysis["status_code"], 404)
        self.assertEqual(analysis["is_valid_response"], "Error")
        self.assertTrue(analysis["response_body"], "Empty")
        self.assertIn("security_headers_present", analysis)

    @patch("builtins.print")
    def test_print_analysis(self, mock_print):
        analyzer = ResponseAnalyzer(PromptPurpose.INPUT_VALIDATION)
        analysis = analyzer.analyze_response(self.raw_http_response)
        analysis_str = analyzer.print_analysis(analysis)

        # Check that the correct calls were made to print
        self.assertIn("HTTP Status Code: 404", analysis_str)
        self.assertIn("Response Body: Empty", analysis_str)
        self.assertIn("Security Headers Present: Yes", analysis_str)


if __name__ == "__main__":
    unittest.main()
