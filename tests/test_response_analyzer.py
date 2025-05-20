import unittest
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_analyzer import ResponseAnalyzer


class TestResponseAnalyzer(unittest.TestCase):

    def setUp(self):
        self.auth_headers = (
            "HTTP/1.1 200 OK\n"
            "Authorization: Bearer token\n"
            "X-Ratelimit-Limit: 1000\n"
            "X-Ratelimit-Remaining: 998\n"
            "X-Ratelimit-Reset: 1723802321\n"
            "\n"
            '[{"message": "Welcome!"}]'
        )

        self.error_body = (
            "HTTP/1.1 403 Forbidden\n"
            "Content-Type: application/json\n"
            "\n"
            '[{"error": "Access denied"}]'
        )

        self.validation_fail = (
            "HTTP/1.1 400 Bad Request\n"
            "X-Content-Type-Options: nosniff\n"
            "\n"
            '[{"error": "Invalid input"}]'
        )

    def test_parse_http_response_success(self):
        analyzer = ResponseAnalyzer()
        status, headers, body = analyzer.parse_http_response(self.auth_headers)

        self.assertEqual(200, status)
        self.assertIn("Authorization", headers)
        if isinstance(body, dict):
            msg = body.get("message")
            self.assertEqual( "Welcome!",msg )

    def test_parse_http_response_invalid(self):
        analyzer = ResponseAnalyzer()
        status, headers, body = analyzer.parse_http_response(self.error_body)

        self.assertEqual( 403, status)
        if isinstance(body, dict):
            msg = body.get("message")

            self.assertEqual( "Access denied", msg)

    def test_analyze_authentication(self):
        analyzer = ResponseAnalyzer(PromptPurpose.AUTHENTICATION)
        result = analyzer.analyze_response(self.auth_headers)

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["authentication_status"], "Authenticated")
        self.assertTrue(result["auth_headers_present"])
        self.assertIn("X-Ratelimit-Limit", result["rate_limiting"])

    def test_analyze_input_validation_invalid(self):
        analyzer = ResponseAnalyzer(PromptPurpose.INPUT_VALIDATION)
        result = analyzer.analyze_response(self.validation_fail)

        self.assertEqual(result["status_code"], 400)
        self.assertEqual(result["is_valid_response"], "Invalid")
        self.assertTrue(result["security_headers_present"])

    def test_is_valid_input_response(self):
        analyzer = ResponseAnalyzer()
        self.assertEqual(analyzer.is_valid_input_response(200, "data"), "Valid")
        self.assertEqual(analyzer.is_valid_input_response(400, "error"), "Invalid")
        self.assertEqual(analyzer.is_valid_input_response(500, "error"), "Error")
        self.assertEqual(analyzer.is_valid_input_response(999, "???"), "Unexpected")

    def test_document_findings(self):
        analyzer = ResponseAnalyzer()
        document = analyzer.document_findings(
            status_code=403,
            headers={"Content-Type": "application/json"},
            body="Access denied",
            expected_behavior="Access should be allowed",
            actual_behavior="Access denied"
        )
        self.assertEqual(document["Status Code"], 403)
        self.assertIn("Access denied", document["Actual Behavior"])

    def test_print_analysis_output_structure(self):
        analyzer = ResponseAnalyzer(PromptPurpose.INPUT_VALIDATION)
        result = analyzer.analyze_response(self.validation_fail)
        printed = analyzer.print_analysis(result)

        self.assertIn("HTTP Status Code: 400", printed)
        self.assertIn("Valid Response: Invalid", printed)
        self.assertIn("Security Headers Present", printed)

    def test_report_issues_found(self):
        analyzer = ResponseAnalyzer()
        document = analyzer.document_findings(
            status_code=200,
            headers={},
            body="test",
            expected_behavior="User not authenticated",
            actual_behavior="User is authenticated"
        )
        # Just ensure no exceptions, prints okay
        analyzer.report_issues(document)


if __name__ == "__main__":
    unittest.main()
