import datetime
import os
import pydantic_core
import time
import yaml

from dataclasses import dataclass, field
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from rich.panel import Panel
from typing import List, Any, Union, Dict

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.record_note import RecordNote
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.common_patterns import RoundBasedUseCase
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from hackingBuddyGPT.utils import LLMResult, tool_message, ui
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib
from hackingBuddyGPT.usecases import use_case

Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any

@use_case("simple_web_api_documentation", "Minimal implementation of a web api documentation use case")
@dataclass
class SimpleWebAPIDocumentation(RoundBasedUseCase):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://jsonplaceholder.typicode.com")
    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_http_methods_found: bool = False

    # Parameter specifying the pattern description for expected HTTP methods in the API response
    http_method_description: str = parameter(
        desc="Pattern description for expected HTTP methods in the API response",
        default="A string that represents an HTTP method (e.g., 'GET', 'POST', etc.)."
    )

    # Parameter specifying the template used to format HTTP methods in API requests
    http_method_template: str = parameter(
        desc="Template used to format HTTP methods in API requests. The {method} placeholder will be replaced by actual HTTP method names.",
        default="{method} request"
    )

    # Parameter specifying the expected HTTP methods as a comma-separated list
    http_methods: str = parameter(
        desc="Comma-separated list of HTTP methods expected to be used in the API response.",
        default="GET,POST,PUT,PATCH,DELETE"
    )

    def init(self):
        super().init()
        self.openapi_spec = self.openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Generated API Documentation",
            "version": "1.0",
            "description": "Automatically generated description of the API."
        },
        "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
        "endpoints": {}
    }
        self._prompt_history.append(
            {
                "role": "system",
                "content": f"You're tasked with documenting the REST APIs of a website hosted at {self.host}. "
                           f"Your main goal is to comprehensively explore the APIs endpoints and responses, and then document your findings in form of a OpenAPI specification."
                           f"Start with an empty OpenAPI specification.\n"
                           f"Maintain meticulousness in documenting your observations as you traverse the APIs. This will streamline the documentation process.\n"
                           f"Avoid resorting to brute-force methods. All essential information should be accessible through the API endpoints.\n"

            })
        self.prompt_engineer = PromptEngineer(
            strategy=PromptStrategy.CHAIN_OF_THOUGHT,
            api_key=self.llm.api_key,
            history=self._prompt_history)

        self._context["host"] = self.host
        sett = set(self.http_method_template.format(method=method) for method in self.http_methods.split(","))
        self._capabilities = {
            "submit_http_method": SubmitFlag(self.http_method_description,
                                             sett,
                                             success_function=self.all_http_methods_found),
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(self._context["notes"]),
        }
        self.current_time = datetime.datetime.now()

    def all_http_methods_found(self):
        self.console.print(Panel("All HTTP methods found! Congratulations!", title="system"))
        self._all_http_methods_found = True

    def perform_round(self, turn: int, FINAL_ROUND=20):

        with self.console.status("[bold green]Asking LLM for a new command..."):
            # generate prompt
            prompt = self.prompt_engineer.generate_prompt(doc=True)

            tic = time.perf_counter()

            response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model,
                                                                                               messages=prompt,
                                                                                               response_model=capabilities_to_action_model(
                                                                                                   self._capabilities))
            toc = time.perf_counter()

            message = completion.choices[0].message

            tool_call_id = message.tool_calls[0].id
            command = pydantic_core.to_json(response).decode()
            self.console.print(Panel(command, title="assistant"))

            self._prompt_history.append(message)
            content = completion.choices[0].message.content

            answer = LLMResult(content, str(prompt),
                               content, toc - tic, completion.usage.prompt_tokens,
                               completion.usage.completion_tokens)

        with self.console.status("[bold green]Executing that command..."):
            result = response.execute()

            self.console.print(Panel(result, title="tool"))
            result_str = self.parse_http_status_line(result)
            self._prompt_history.append(tool_message(result_str, tool_call_id))
            if result_str == '200 OK':
                self.update_openapi_spec(response )

        self.log_db.add_log_query(self._run_id, turn, command, result, answer)
        self.write_openapi_to_yaml()
        return self._all_http_methods_found

    def parse_http_status_line(self, status_line):
        if status_line is None or status_line == "Not a valid flag":
            return status_line
        else:
            # Split the status line into components
            parts = status_line.split(' ', 2)

            # Check if the parts are at least three in number
            if len(parts) >= 3:
                protocol = parts[0]  # e.g., "HTTP/1.1"
                status_code = parts[1]  # e.g., "200"
                status_message = parts[2].split("\r\n")[0]  # e.g., "OK"
                print(f'status code:{status_code}, status msg:{status_message}')
                return str(status_code + " " + status_message)
            else:
                raise ValueError("Invalid HTTP status line")

    def has_no_numbers(self,path):
        for char in path:
            if char.isdigit():
                return False
        return True
    def update_openapi_spec(self, response):
        # This function should parse the request and update the OpenAPI specification
        # For the purpose of this example, let's assume it parses JSON requests and updates paths
            request = response.action
            path = request.path
            method = request.method
            if path and method:
                if path not in self.openapi_spec['endpoints']:#and self.has_no_numbers(path):
                    self.openapi_spec['endpoints'][path] = {}
                self.openapi_spec['endpoints'][path][method.lower()] = {
                    "summary": f"{method} operation on {path}",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}  # Simplified for example
                                }
                            }
                        }
                    }
                }

    def write_openapi_to_yaml(self, filename='openapi_spec.yaml'):
        """Write the OpenAPI specification to a YAML file."""
        try:
            openapi_data = {
                "openapi": self.openapi_spec["openapi"],
                "info": self.openapi_spec["info"],
                "servers": self.openapi_spec["servers"],
                "paths": self.openapi_spec["endpoints"]
            }

            # Ensure the directory exists
            file_path = filename.split(".yaml")[0]
            file_name = filename.split(".yaml")[0] + "_"+ self.current_time.strftime("%Y-%m-%d %H:%M:%S")+".yaml"
            os.makedirs(file_path, exist_ok=True)

            with open(os.path.join(file_path, file_name), 'w') as yaml_file:
                yaml.dump(openapi_data, yaml_file, allow_unicode=True, default_flow_style=False)
            self.console.print(f"[green]OpenAPI specification written to [bold]{filename}[/bold].")
        except Exception as e:
            raise Exception(e)

            #self.console.print(f"[red]Error writing YAML file: {e}")
    def write_openapi_to_yaml2(self, filename='openapi_spec.yaml'):
        """Write the OpenAPI specification to a YAML file."""
        try:
           # self.setup_yaml()  # Configure YAML to handle complex types
            with open(filename, 'w') as yaml_file:
                yaml.dump(self.openapi_spec, yaml_file, allow_unicode=True, default_flow_style=False)
            self.console.print(f"[green]OpenAPI specification written to [bold]{filename}[/bold].")
        except TypeError as e:
            raise Exception(e)
            #self.console.print(f"[red]Error writing YAML file: {e}")

    def represent_dict_order(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data.items())

    def setup_yaml(self):
        """Configure YAML to output OrderedDicts as regular dicts (helpful for better YAML readability)."""
        yaml.add_representer(dict, self.represent_dict_order)
