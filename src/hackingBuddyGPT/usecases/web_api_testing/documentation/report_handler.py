import os
from datetime import datetime
import uuid
from typing import List
from enum import Enum

class ReportHandler:
    """
    A handler for creating and managing report files that document operations and data.

    Attributes:
        file_path (str): The path to the directory where report files are stored.
        report_name (str): The full path to the current report file being written to.
        report (file): The file object for the report, opened for writing data.
    """

    def __init__(self):
        """
        Initializes the ReportHandler by setting up the file path for reports,
        creating the directory if it does not exist, and preparing a new report file.
        """
        current_path: str = os.path.dirname(os.path.abspath(__file__))
        self.file_path: str = os.path.join(current_path, "reports")

        if not os.path.exists(self.file_path):
            os.mkdir(self.file_path)

        self.report_name: str = os.path.join(self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
        try:
            self.report = open(self.report_name, "x")
        except FileExistsError:
            # Retry with a different name using a UUID to ensure uniqueness
            self.report_name = os.path.join(self.file_path,
                                            f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4().hex}.txt")
            self.report = open(self.report_name, "x")

    def write_endpoint_to_report(self, endpoint: str) -> None:
        """
        Writes an endpoint string to the report file.

        Args:
            endpoint (str): The endpoint information to be recorded in the report.
        """
        with open(self.report_name, 'a') as report:
            report.write(f'{endpoint}\n')

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
                lines = item.split("\n")
                filtered_lines = [line for line in lines if "note recorded" not in line]
                report.write("\n".join(filtered_lines) + "\n")


