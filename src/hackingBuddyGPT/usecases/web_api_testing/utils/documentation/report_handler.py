import os.path
from datetime import datetime


class ReportHandler(object):

    def __init__(self):
        current_path = os.path.dirname(os.path.abspath(__file__))

        self.file_path = os.path.join(current_path,"reports")
        if not os.path.exists(self.file_path):
            os.mkdir(self.file_path)
        self.report_name = os.path.join(self.file_path, f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

        self.report = open(self.report_name, "x")

    def write_endpoint_to_report(self, endpoint):
        self.report = open(self.report_name, 'a')
        self.report.write(f'{endpoint}\n')
        self.report.close()
    def write_analysis_to_report(self, analysis, purpose):
        self.report = open(self.report_name, 'a')
        self.report.write(f'{purpose.name}')
        self.report.write(analysis)
        self.report.close()