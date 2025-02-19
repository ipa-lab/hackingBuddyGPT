import os
import re
import textwrap
import uuid
from datetime import datetime
from enum import Enum
from typing import List
from fpdf import FPDF


class ReportHandler:
    """
    A handler for creating and managing report files that document operations and data.

    Attributes:
        file_path (str): The path to the directory where report files are stored.
        report_name (str): The full path to the current report file being written to.
        report (file): The file object for the report, opened for writing data.
    """

    def __init__(self, config):
        """
        Initializes the ReportHandler by setting up the file path for reports,
        creating the directory if it does not exist, and preparing a new report file.
        """
        current_path: str = os.path.dirname(os.path.abspath(__file__))
        print(f'config: {config}')
        print(f'config: {config.get("name")}')
        self.file_path: str = os.path.join(current_path, "reports", config.get("name"))
        self.vul_file_path: str = os.path.join(current_path, "vulnerabilities",config.get("name") )

        os.makedirs(self.file_path, exist_ok=True)
        os.makedirs(self.vul_file_path, exist_ok=True)

        if not os.path.exists(self.file_path):
            os.mkdir(self.file_path)

        if not os.path.exists(self.vul_file_path):
            os.mkdir(self.vul_file_path)

        self.report_name: str = os.path.join(
            self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )
        self.vul_report_name: str = os.path.join(
            self.vul_file_path, f"vul_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )

        self.vulnerabilities_counter = 0


        # Initialize the PDF object
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)

        try:
            self.report = open(self.report_name, "x")
            self.vul_report = open(self.vul_report_name, "x")
        except FileExistsError:
            # Retry with a different name using a UUID to ensure uniqueness
            self.report_name = os.path.join(
                self.file_path,
                f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4().hex}.txt",
            )
            self.report = open(self.report_name, "x")

    def write_endpoint_to_report(self, endpoint: str) -> None:
        """
        Writes an endpoint string to the report file.

        Args:
            endpoint (str): The endpoint information to be recorded in the report.
        """
        with open(self.report_name, "a") as report:
            report.write(f"{endpoint}\n")

        self.pdf.set_font("Arial", size=12)
        self.pdf.multi_cell(0, 10, f"Endpoint: {endpoint}")

    def write_analysis_to_report(self, analysis: List[str], purpose: Enum) -> None:
        """
        Writes an analysis result and its purpose to the report file.

        Args:
            analysis (List[str]): The analysis data to be recorded.
            purpose (Enum): An enumeration that describes the purpose of the analysis.
        """
        # Open the file in read mode to check if the purpose already exists
        try:
            with open(self.report_name, 'r') as report:
                content = report.read()
        except FileNotFoundError:
            # If file does not exist, treat as if the purpose doesn't exist
            content = ""

        # Check if the purpose.name is already in the content
        if purpose.name not in content:
            with open(self.report_name, 'a') as report:
                report.write(
                    '-------------------------------------------------------------------------------------------\n')
                report.write(f'{purpose.name}:\n')

        # Write the analysis data
        with open(self.report_name, 'a') as report:
            for item in analysis:
                filtered_lines = [line for line in item.split("\n") if "note recorded" not in line]
                report.write("\n".join(filtered_lines) + "\n")

        # Set up PDF formatting
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.text(10, self.pdf.get_y() + 10, f"Purpose: {purpose.name}")
        self.pdf.set_font("Arial", size=12)

        # Write filtered analysis to PDF
        self.pdf.set_font("Arial", size=10)

        for item in analysis:
            filtered_lines = [line for line in item.split("\n") if "note recorded" not in line]

            # Wrap text properly
            wrapped_text = [textwrap.fill(line, width=80) for line in filtered_lines if line.strip()]

            # Print to debug
            print(f"Writing to PDF: {wrapped_text}")

            # Write to PDF using text() for precise positioning
            y_position = self.pdf.get_y() + 5  # Increment position for each line
            for line in wrapped_text:
                self.pdf.text(10, y_position, line)
                y_position += 5  # Move cursor for next line

            # Move cursor down for next section
            self.pdf.set_y(y_position + 5)
    def save_report(self) -> None:
        """
        Finalizes and saves the PDF report to the file system.
        """
        report_name = self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        self.pdf.output(report_name)

    def write_vulnerability_to_report(self, test_step, raw_response, current_substep):
        """
            Checks the given raw HTTP response against the test_data (which includes expected_response_code
            and success/failure messages). Writes the result ("No Vulnerability found." or "Vulnerability found.")
            into a text file, using the name of the test case in the report.

            :param test_step: A dictionary containing test information, e.g.:
                {
                    'conditions': {
                        'if_successful': 'No Vulnerability found.',
                        'if_unsuccessful': 'Vulnerability found.'
                    },
                    'expected_response_code': ['200 OK', '201 Created'],
                    'step': 'Create an account by sending ...'
                    ...
                }
            :param raw_response: The full raw HTTP response string, e.g.:
                'HTTP/1.1 200\\r\\n'
                'Server: openresty/1.25.3.1\\r\\n'
                ...
                '{"message":"User registered successfully!","status":200}'
            :param output_file: The filename where the vulnerability report is appended.
            """

        # ---------------------------------------------------------
        # 1) Extract status code and status message from response
        # ---------------------------------------------------------
        # Look for a line like: HTTP/1.1 200 OK or HTTP/1.1 201 Created
        # We'll capture both the numeric code and any trailing status text.
        match = re.search(r"^HTTP/\d\.\d\s+(\d+)(?:\s+(.*))?", raw_response, re.MULTILINE)
        if match:
            status_code = match.group(1).strip()  # e.g. "200"
            status_message = match.group(2) or ""  # e.g. "OK"
            status_message = status_message.strip()
            # Combine them to get something like "200 OK" for comparison
            full_status_line = (status_code + " " + status_message).strip()
        else:
            # If we can't find an HTTP status line, treat it as suspicious
            status_code = None
            full_status_line = ""

        # ---------------------------------------------------------
        # 2) Determine if the response is "successful" based on test_data
        # ---------------------------------------------------------
        # The test_data dictionary includes an 'expected_response_code' list,
        # e.g. ["200 OK", "201 Created"]. We compare our full_status_line
        # with each expected string (case-insensitive).
        expected_codes = test_step.get('expected_response_code', [])
        conditions = test_step.get('conditions', {})
        successful_msg = conditions.get('if_successful', "No Vulnerability found.")
        unsuccessful_msg = conditions.get('if_unsuccessful', "Vulnerability found.")

        # A simple case-insensitive check. Alternatively, parse numeric code
        print(f'expected_codes: {expected_codes}')

        success = any(
            str(status_code).strip() == str(expected.split()[0]).strip() and len(expected.split()[0].strip()) == 3 and expected.split()[0].strip().isdigit()  # Ensure first word is a 3-digit number
            for expected in expected_codes if expected.strip()  # Ensure no empty or space-only entries in the list
        )

        # ---------------------------------------------------------
        # 3) Compose the report line
        # ---------------------------------------------------------
        test_case_name = test_step.get('purpose', "Unnamed Test Case")
        step = test_step.get('step', "No step")
        expected = test_step.get('expected_response_code', "No expected result")
        if (not success):
            # Vulnerability found
            self.vulnerabilities_counter += 1
            report_line = f"Test Name: {test_case_name}\nStep:{step}\nExpected Result:{expected}\nActual Result:{status_code}\n{unsuccessful_msg}\nNumber of found vulnerabilities:{self.vulnerabilities_counter}\n"
            # ---------------------------------------------------------
            # 4) Write the result into a text file
            # ---------------------------------------------------------
            with open(self.vul_report_name, "a", encoding="utf-8") as f:
                f.write(report_line)



