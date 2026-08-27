import json
import os
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List


class ReportHandler:
    """
    Collects results during an automated web API testing run and renders a single
    unified Markdown report (tested endpoints, analysis, and discovered
    vulnerabilities).

    Results are buffered in memory and the report file is re-rendered after each
    write, so the report on disk is always current (crash-resilient) while the
    sections stay cleanly grouped.

    Attributes:
        file_path (str): Directory where the report is stored (reports/<name>).
        report_name (str): Full path to the current Markdown report file.
        vulnerabilities_counter (int): Number of vulnerabilities found so far.
    """

    def __init__(self, config):
        """
        Initializes the ReportHandler, prepares the report directory/file, and
        sets up the in-memory buffers.

        Args:
            config (dict): Configuration dictionary containing metadata like the
                test name.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.name = config.get("name")
        self.file_path = os.path.join(current_path, "reports", self.name)
        os.makedirs(self.file_path, exist_ok=True)

        self._created_at = datetime.now()
        self.report_name = os.path.join(
            self.file_path, f"report_{self._created_at.strftime('%Y-%m-%d_%H-%M-%S')}.md"
        )

        self.vulnerabilities_counter = 0
        self._endpoints: List[str] = []
        self._analysis: Dict[str, List[str]] = {}
        self._findings: List[str] = []

        self._render()

    def write_endpoint_to_report(self, endpoint: str) -> None:
        """
        Records a single tested endpoint.

        Args:
            endpoint (str): The tested endpoint.
        """
        if endpoint not in self._endpoints:
            self._endpoints.append(endpoint)
        self._render()

    def write_analysis_to_report(self, analysis: List[str], purpose: Enum) -> None:
        """
        Records analysis data, grouped by purpose.

        Args:
            analysis (List[str]): List of strings with analysis output.
            purpose (Enum): Enum representing the analysis type or purpose.
        """
        bucket = self._analysis.setdefault(purpose.name, [])
        for item in analysis:
            filtered_lines = [line for line in item.split("\n") if "note recorded" not in line]
            text = "\n".join(filtered_lines).strip()
            if text:
                bucket.append(text)
        self._render()

    def write_vulnerability_to_report(self, test_step, test_over_step, raw_response, current_substep):
        """
        Analyzes an HTTP response and records whether a vulnerability was detected.

        Args:
            test_step (dict): Metadata about the current test step, including
                expected codes and messages.
            test_over_step (dict): Metadata about the enclosing test phase.
            raw_response (str): Full raw HTTP response string.
            current_substep: Label or identifier for the current test substep.
        """
        match = re.search(r"^HTTP/\d\.\d\s+(\d+)(?:\s+(.*))?", raw_response, re.MULTILINE)
        if match:
            status_code = match.group(1).strip()
        else:
            status_code = None

        test_case_purpose = test_step.get('purpose', "Unnamed Test Case")
        test_case_name = test_over_step.get("phase_title").split("Phase: ")[1]
        step = test_step.get('step', "No step")
        expected = test_step.get('expected_response_code', "No expected result")

        security = test_step.get("security") or ""
        if "only one id" in security:
            headers, body = raw_response.split('\r\n\r\n', 1)
            body = json.loads(body)
            if len(body) > 1:
                self._add_finding(
                    test_case_purpose, test_case_name, step,
                    expected="Only one",
                    actual="More than one id returned",
                )
            elif "message" in body:
                self._add_finding(
                    test_case_purpose, test_case_name, step,
                    expected="Only necesary information should be returned.",
                    actual="Too much information was logged.",
                )

        expected_codes = test_step.get('expected_response_code', [])
        conditions = test_step.get('conditions', {})
        unsuccessful_msg = conditions.get('if_unsuccessful', "Vulnerability found.")

        success = any(
            isinstance(expected_code, str) and
            str(status_code).strip() == str(expected_code.split()[0]).strip()
            and expected_code.split()[0].strip().isdigit()
            for expected_code in expected_codes if isinstance(expected_code, str) and expected_code.strip()
        )

        if not success:
            self._add_finding(
                test_case_purpose, test_case_name, step,
                expected=expected,
                actual=status_code,
                note=unsuccessful_msg,
            )
        self._render()

    def save_report(self) -> None:
        """
        Finalizes the Markdown report on disk.
        """
        self._render()

    def _add_finding(self, purpose, name, step, expected, actual, note=""):
        """Buffers one vulnerability finding as a Markdown block."""
        self.vulnerabilities_counter += 1
        lines = [
            f"### Finding {self.vulnerabilities_counter}: {purpose}",
            "",
            f"- **Test Name:** {name}",
            f"- **Step:** {step}",
            f"- **Expected Result:** {expected}",
            f"- **Actual Result:** {actual}",
        ]
        if note:
            lines.append(f"- **Note:** {note}")
        lines.append("")
        self._findings.append("\n".join(lines))

    def _render(self) -> None:
        """Overwrites the report file with the current unified Markdown document."""
        lines = [
            f"# Web API Testing Report — {self.name}",
            "",
            f"_Generated {self._created_at.strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
            "## Endpoints tested",
            "",
        ]
        lines += [f"- {ep}" for ep in self._endpoints] if self._endpoints else ["_None recorded._"]

        lines += ["", "## Analysis", ""]
        if self._analysis:
            for purpose_name, items in self._analysis.items():
                lines += [f"### {purpose_name}", ""]
                for item in items:
                    lines += [item, ""]
        else:
            lines += ["_None recorded._", ""]

        lines += ["## Vulnerabilities", ""]
        if self._findings:
            lines += self._findings
        else:
            lines += ["_None found._", ""]

        with open(self.report_name, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")
