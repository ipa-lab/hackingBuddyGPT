import os.path
from datetime import datetime

import os
from datetime import datetime


class ReportHandler(object):
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
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_path, "reports")

        if not os.path.exists(self.file_path):
            os.mkdir(self.file_path)

        self.report_name = os.path.join(self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
        self.report = open(self.report_name, "x")

    def write_endpoint_to_report(self, endpoint):
        """
        Writes an endpoint string to the report file.

        Args:
            endpoint (str): The endpoint information to be recorded in the report.
        """
        self.report = open(self.report_name, 'a')
        self.report.write(f'{endpoint}\n')
        self.report.close()

    def write_analysis_to_report(self, analysis, purpose):
        """
        Writes an analysis result and its purpose to the report file.

        Args:
            analysis (str): The analysis data to be recorded.
            purpose (Enum): An enumeration that describes the purpose of the analysis.
        """
        self.report = open(self.report_name, 'a')
        self.report.write(f'{purpose.name}:\n')
        for item in analysis:
            for line in item.split("\n"):
                if line.__contains__("note recorded"):
                    continue
                else:
                    self.report.write(str(line) +"\n")
        self.report.close()
