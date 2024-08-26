import os.path
from dataclasses import field
from typing import List, Any, Union, Dict

import pydantic_core
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from rich.panel import Panel

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.usecases.agents import Agent
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import PromptContext
from hackingBuddyGPT.usecases.web_api_testing.utils.documentation import OpenAPISpecificationParser
from hackingBuddyGPT.usecases.web_api_testing.utils.documentation.report_handler import ReportHandler
from hackingBuddyGPT.usecases.web_api_testing.utils.llm_handler import LLMHandler
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler
from hackingBuddyGPT.utils import tool_message
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib
from hackingBuddyGPT.usecases.base import AutonomousAgentUseCase, use_case

Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any
openapi_spec_filename = "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/utils/openapi_spec/openapi_spec_2024-08-16_14-14-07.yaml"
class SimpleWebAPITesting(Agent):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.)."
    )
    http_method_template: str = parameter(
        desc="Template used to format HTTP methods in API requests. The {method} placeholder will be replaced by actual HTTP method names.",
        default="{method}"
    )
    http_methods: str = parameter(
        desc="Comma-separated list of HTTP methods expected to be used in the API response.",
        default="GET,POST,PUT,DELETE"
    )

    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False



    def init(self):
        """
        Initializes the SimpleWebAPITesting use case by setting up the context, response handler,
        LLM handler, capabilities, and the initial prompt.
        """
        super().init()
        if os.path.exists(openapi_spec_filename):
            self.openapi_specification = OpenAPISpecificationParser(openapi_spec_filename).api_data
        self._context["host"] = self.host
        self._setup_capabilities()
        self.llm_handler = LLMHandler(self.llm, self._capabilities)
        self.response_handler = ResponseHandler(self.llm_handler)

        self.report_handler = ReportHandler()
        self._setup_initial_prompt()


    def _setup_initial_prompt(self):
        """
        Sets up the initial prompt for the LLM. The prompt provides instructions for the LLM
        to evaluate the REST APIs of the specified host and to document findings.
        """
        initial_prompt = {
            "role": "system",
            "content": (
                f"You're a seasoned API tester tasked with evaluating the REST APIs of a website hosted at {self.host}. "
                f"Your primary objective is to thoroughly explore the APIs, understanding their endpoints, parameters, and responses, "
                f"and then devise and execute potential exploits. Be diligent in documenting your findings as you navigate through the APIs. "
                f"Avoid resorting to brute-force tactics. All necessary information can be obtained from the API endpoints themselves. "
                f"Remember, if you encounter an HTTP method ({self.http_method_description}), promptly submit it as it is of utmost importance."
            )
        }
        self._prompt_history.append(initial_prompt)
        handlers = (self.llm_handler, self.response_handler)
        if os.path.exists(openapi_spec_filename):
            schemas = self.openapi_specification["components"]["schemas"]
        else:
            schemas = {}
        self.prompt_engineer = PromptEngineer(strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                                              history=self._prompt_history,
                                              handlers=handlers,
                                              context=PromptContext.PENTESTING,
                                              rest_api=self.host,
                                              schemas=schemas)



    def all_http_methods_found(self):
        """
        Handles the event when all HTTP methods are found. Displays a congratulatory message
        and sets the _all_http_methods_found flag to True.
        """
        self._log.console.print(Panel("All HTTP methods found! Congratulations!", title="system"))
        self._all_http_methods_found = True

    def _setup_capabilities(self):
        """
        Sets up the capabilities required for the use case. Initializes HTTP request capabilities,
        note recording capabilities, and HTTP method submission capabilities based on the provided
        configuration.
        """
        methods_set = {self.http_method_template.format(method=method) for method in self.http_methods.split(",")}
        notes = self._context["notes"]
        self._capabilities = {
            "submit_http_method": HTTPRequest(self.host),
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(notes)
        }

    def perform_round(self, turn: int):
        """
        Performs a single round of interaction with the LLM. Generates a prompt, sends it to the LLM,
        and handles the response.

        Args:
            turn (int): The current round number.
            FINAL_ROUND (int, optional): The final round number. Defaults to 30.
        """
        prompt = self.prompt_engineer.generate_prompt(turn)
        response, completion = self.llm_handler.call_llm(prompt)
        self._handle_response(completion, response, self.prompt_engineer.purpose)

    def _handle_response(self, completion, response, purpose):
        """
        Handles the response from the LLM. Parses the response, executes the necessary actions,
        and updates the prompt history.

        Args:
            completion (Any): The completion object from the LLM.
            response (Any): The response object from the LLM.
        """
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        command = pydantic_core.to_json(response).decode()
        self._log.console.print(Panel(command, title="assistant"))
        self._prompt_history.append(message)

        with self._log.console.status("[bold green]Executing that command..."):
            result = response.execute()
            self._log.console.print(Panel(result[:30], title="tool"))
            if not isinstance(result, str):
                endpoint = str(response.action.path).split('/')[1]
                self.report_handler.write_endpoint_to_report(endpoint)
            self._prompt_history.append(tool_message(str(result), tool_call_id))

            analysis = self.response_handler.evaluate_result(result, purpose, self._prompt_history)
            self.report_handler.write_analysis_to_report(analysis=analysis, purpose=self.prompt_engineer.purpose)
            #self._prompt_history.append(tool_message(str(analysis), tool_call_id))




        return self.all_http_methods_found()
@use_case("Minimal implementation of a web API testing use case")
class SimpleWebAPITestingUseCase(AutonomousAgentUseCase[SimpleWebAPITesting]):
    pass