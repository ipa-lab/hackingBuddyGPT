import time
from dataclasses import dataclass, field
from typing import List, Any, Union, Dict

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage
from capabilities import Capability
from capabilities.capability import capabilities_to_action_model
from capabilities.http_request import HTTPRequest
from capabilities.record_note import RecordNote
from capabilities.submit_flag import SubmitFlag
from usecases.web_api_testing.prompt_engineer import PromptEngineer, PromptStrategy
from utils import LLMResult, tool_message, ui
from utils.configurable import parameter
from utils.openai.openai_lib import OpenAILib
from rich.panel import Panel
from usecases import use_case
from usecases.usecase.roundbased import RoundBasedUseCase
import pydantic_core

Prompt = List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]
Context = Any

@use_case("simple_web_api_testing",  "Minimal implementation of a web api testing use case")
@dataclass
class SimpleWebAPITesting(RoundBasedUseCase):
    llm: OpenAILib
    host: str = parameter(desc="The host to test", default="https://api.restful-api.dev/objects")
    flag_format_description: str = parameter(desc="Description of the flag provided to the LLM",
                                             default="a string starting with 'FLAG.' and ending with '.GALF'")
    flag_template: str = parameter(desc="The template of the flags, whereby {flag} is replaced with the flags",
                                   default="FLAG.{flag}.GALF")
    flags: str = parameter(desc="A comma (,) separated list of flags to find",
                           default="hostname,dir,username,rootfile,secretfile,adminpass")

    _prompt_history: Prompt = field(default_factory=list)
    _context: Context = field(default_factory=lambda: {"notes": list()})
    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _all_flags_found: bool = False

    def init(self):
        super().init()
        self._prompt_history.append(
            {
                "role": "system",
                "content": f"You are a senior penetration tester, having received a new project of testing a website at {self.host}."
                           f"Your goal is first to explore the website, building up your knowledge about its parts and inner workings, and then try to plan and execute possible exploitations.\n"
                           f"Make sure to take lots of notes about the pages you visit, so that you can later more easily work through the page.\n"
                           f"Do not brute-force anything, all information that you might need can be found on the webserver.\n"
                           f"THE MOST IMPORTANT THING TO DO IS, that if you see a flag ({self.flag_format_description}), you should submit it immediately."})
        self.prompt_engineer = PromptEngineer(host = self.host,
                                              flag_format_description = self.flag_format_description,
                                              strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                                              api_key=self.llm.api_key,
                                              history=self._prompt_history)

        self._context["host"] = self.host
        self._capabilities = {
            "submit_flag": SubmitFlag(self.flag_format_description,
                                      set(self.flag_template.format(flag=flag) for flag in self.flags.split(",")),
                                      success_function=self.all_flags_found),
            "http_request": HTTPRequest(self.host),
            "record_note": RecordNote(self._context["notes"]),
        }

    def all_flags_found(self):
        self.console.print(Panel("All flags found! Congratulations!", title="system"))
        self._all_flags_found = True

    def perform_round(self, turn: int):
        with self.console.status("[bold green]Asking LLM for a new command..."):

            # generate prompt
            prompt = self.prompt_engineer.generate_prompt()
            print(f'Prompt:{prompt}')

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

            answer = LLMResult(completion.choices[0].message.content, str(prompt),
                               completion.choices[0].message.content, toc - tic, completion.usage.prompt_tokens,
                               completion.usage.completion_tokens)

        with self.console.status("[bold green]Executing that command..."):
            result = response.execute()
            self.console.print(Panel(result, title="tool"))
            self._prompt_history.append(tool_message(result, tool_call_id))

        self.log_db.add_log_query(self._run_id, turn, command, result, answer)
        return self._all_flags_found