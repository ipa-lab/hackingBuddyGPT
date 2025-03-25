class ReportHandler:
    """
    A handler for creating and managing reports during automated web API testing.

    This class creates both text and PDF reports documenting tested endpoints, analysis results,
    and any vulnerabilities discovered based on HTTP responses.

    Attributes:
        file_path (str): Path to the directory where general reports are stored.
        vul_file_path (str): Path to the directory for vulnerability-specific reports.
        report_name (str): Full path to the current report text file.
        vul_report_name (str): Full path to the vulnerability report text file.
        pdf (FPDF): An FPDF object used to generate a PDF version of the report.
        vulnerabilities_counter (int): Counter tracking the number of vulnerabilities found.
    """

    def __init__(self, config):
        """
        Initializes the ReportHandler, prepares report and vulnerability file paths, and creates
        necessary directories and files.

        Args:
            config (dict): Configuration dictionary containing metadata like the test name.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "reports", config.get("name"))
        self.vul_file_path = os.path.join(current_path, "vulnerabilities", config.get("name"))

        os.makedirs(self.file_path, exist_ok=True)
        os.makedirs(self.vul_file_path, exist_ok=True)

        self.report_name = os.path.join(
            self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )
        self.vul_report_name = os.path.join(
            self.vul_file_path, f"vul_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )

        self.vulnerabilities_counter = 0

        # Initialize PDF
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)

        try:
            self.report = open(self.report_name, "x")
            self.vul_report = open(self.vul_report_name, "x")
        except FileExistsError:
            self.report_name = os.path.join(
                self.file_path,
                f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4().hex}.txt",
            )
            self.report = open(self.report_name, "x")

    def write_endpoint_to_report(self, endpoint: str) -> None:
        """
        Writes a single endpoint string to both the text and PDF reports.

        Args:
            endpoint (str): The tested endpoint.
        """
        with open(self.report_name, "a") as report:
            report.write(f"{endpoint}\n")

        self.pdf.set_font("Arial", size=12)
        self.pdf.multi_cell(0, 10, f"Endpoint: {endpoint}")

    def write_analysis_to_report(self, analysis: List[str], purpose: Enum) -> None:
        """
        Writes analysis data to the text and PDF reports, grouped by purpose.

        Args:
            analysis (List[str]): List of strings with analysis output.
            purpose (Enum): Enum representing the analysis type or purpose.
        """
        try:
            with open(self.report_name, 'r') as report:
                content = report.read()
        except FileNotFoundError:
            content = ""

        if purpose.name not in content:
            with open(self.report_name, 'a') as report:
                report.write('-' * 90 + '\n')
                report.write(f'{purpose.name}:\n')

        with open(self.report_name, 'a') as report:
            for item in analysis:
                filtered_lines = [line for line in item.split("\n") if "note recorded" not in line]
                report.write("\n".join(filtered_lines) + "\n")

        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.text(10, self.pdf.get_y() + 10, f"Purpose: {purpose.name}")
        self.pdf.set_font("Arial", size=10)

        for item in analysis:
            filtered_lines = [line for line in item.split("\n") if "note recorded" not in line]
            wrapped_text = [textwrap.fill(line, width=80) for line in filtered_lines if line.strip()]
            y_position = self.pdf.get_y() + 5
            for line in wrapped_text:
                self.pdf.text(10, y_position, line)
                y_position += 5
            self.pdf.set_y(y_position + 5)

    def save_report(self) -> None:
        """
        Saves the PDF version of the report to the file system.
        """
        report_name = os.path.join(
            self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        )
        self.pdf.output(report_name)

    def write_vulnerability_to_report(self, test_step, raw_response, current_substep):
        """
        Analyzes an HTTP response and logs whether a vulnerability was detected.

        Args:
            test_step (dict): Metadata about the current test step, including expected codes and messages.
            raw_response (str): Full raw HTTP response string.
            current_substep (str): Label or identifier for the current test substep.
        """
        match = re.search(r"^HTTP/\d\.\d\s+(\d+)(?:\s+(.*))?", raw_response, re.MULTILINE)
        if match:
            status_code = match.group(1).strip()
            status_message = (match.group(2) or "").strip()
            full_status_line = f"{status_code} {status_message}".strip()
        else:
            status_code = None
            full_status_line = ""

        expected_codes = test_step.get('expected_response_code', [])
        conditions = test_step.get('conditions', {})
        successful_msg = conditions.get('if_successful', "No Vulnerability found.")
        unsuccessful_msg = conditions.get('if_unsuccessful', "Vulnerability found.")

        success = any(
            str(status_code).strip() == str(expected.split()[0]).strip()
            and expected.split()[0].strip().isdigit()
            for expected in expected_codes if expected.strip()
        )

        test_case_name = test_step.get('purpose', "Unnamed Test Case")
        step = test_step.get('step', "No step")
        expected = test_step.get('expected_response_code', "No expected result")

        if not success:
            self.vulnerabilities_counter += 1
            report_line = (
                f"Test Name: {test_case_name}\n"
                f"Step: {step}\n"
                f"Expected Result: {expected}\n"
                f"Actual Result: {status_code}\n"
                f"{unsuccessful_msg}\n"
                f"Number of found vulnerabilities: {self.vulnerabilities_counter}\n\n"
            )
            with open(self.vul_report_name, "a", encoding="utf-8") as f:
                f.write(report_line)
