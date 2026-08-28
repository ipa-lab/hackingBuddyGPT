import re
from typing import Any

from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.web_api.response_analyzer_with_llm import ResponseAnalyzerWithLLM
from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler
from hackingBuddyGPT.utils.web_api.custom_datatypes import Prompt


class ResponseHandler:
    """
    Phase-agnostic response handling shared by the web-API use-cases.

    This base class keeps only the parts both phases use: evaluating a result through the
    LLM-based response analyzer, extracting the key elements of a raw HTTP response, and
    parsing an HTTP status line. The detection/documentation phase's endpoint-exploration
    state machine lives in ``usecases.web_api.detection_response_handler.DetectionResponseHandler``.

    Attributes:
        llm_handler (LLMHandler): An instance of the LLM handler for interacting with the LLM.
        pentesting_information (PenTestingInformation): Pentesting information (pentesting context only).
        response_analyzer (ResponseAnalyzerWithLLM): An instance for analyzing responses with the LLM.
    """

    def __init__(self, llm_handler: LLMHandler, prompt_context: PromptContext, config: Any,
                 prompt_helper: PromptGenerationHelper, pentesting_information: PenTestingInformation = None) -> None:
        self.llm_handler = llm_handler
        self.prompt_helper = prompt_helper
        if prompt_context == PromptContext.PENTESTING:
            self.pentesting_information = pentesting_information
        self.response_analyzer = None

    def set_response_analyzer(self, response_analyzer: ResponseAnalyzerWithLLM) -> None:
        self.response_analyzer = response_analyzer


    def parse_http_status_line(self, status_line: str) -> str:
        """
        Parses an HTTP status line and returns the status code and message.

        Args:
            status_line (str): The HTTP status line to be parsed.

        Returns:
            str: The parsed status code and message.

        Raises:
            ValueError: If the status line is invalid.
        """
        if status_line == "Not a valid HTTP method" or "note recorded" in status_line:
            return status_line
        status_line = status_line.split("\r\n")[0]
        # Regular expression to match valid HTTP status lines
        match = re.match(r"^(HTTP/\d\.\d) (\d{3}) (.*)$", status_line)
        if match:
            protocol, status_code, status_message = match.groups()
            return f"{status_code} {status_message}"
        else:
            raise ValueError(f"{status_line} is an invalid HTTP status line")

    async def evaluate_result(self, result: Any, prompt_history: Prompt, analysis_context: Any) -> Any:
        """
        Evaluates the result using the LLM-based response analyzer.

        Args:
            result (Any): The result to evaluate.
            prompt_history (list): The history of prompts used in the evaluation.

        Returns:
            Any: The evaluation result from the LLM response analyzer.
        """
        self.response_analyzer._prompt_helper = self.prompt_helper
        llm_responses, status_code = await self.response_analyzer.analyze_response(result, prompt_history, analysis_context)
        return llm_responses, status_code

    def extract_key_elements_of_response(self, raw_response: Any) -> str:
        status_code, headers, body = self.response_analyzer.parse_http_response(raw_response)
        return "Status Code: " + str(status_code) + "\nHeaders:" + str(headers) + "\nBody" + str(body)

