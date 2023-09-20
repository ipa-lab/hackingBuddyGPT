import time
import typing

from dataclasses import dataclass
from mako.template import Template
from helper import *

@dataclass
class LLMResult:
    result: typing.Any
    prompt: str
    answer: str
    duration: float = 0
    tokens_query: int = 0
    tokens_response: int = 0

def get_empty_result():
    return LLMResult('', '', '', 0, 0, 0)

class LLMWithState:
    def __init__(self, run_id, llm_connection, history, initial_user, initial_password, hints=None):
        self.llm_connection = llm_connection
        self.initial_user = initial_user
        self.initial_password = initial_password
        self.db = history
        self.run_id = run_id
        self.state = f"""
- this is a linux system
- your low privilege user credentials are {initial_user}:{initial_password}
"""
        self.hints = hints

    def get_next_cmd(self, hostname=''):

        template_file = 'query_next_command.txt'
        model = self.llm_connection.get_model()

        state_size = num_tokens_from_string(model, self.state)

        template = Template(filename='templates/' + template_file)
        template_size = num_tokens_from_string(model, template.source)

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size)

        if self.hints != None:
            hint = self.hints[hostname]
        else:
            hint =''
        result = self.create_and_ask_prompt_text(template_file, user=self.initial_user, password=self.initial_password, history=history, state=self.state, hint=hint)

        # make result backwards compatible
        if result.result.startswith("test_credentials"):
            result.result = {
                "type" : "ssh",
                "username" : result.result.split(" ")[1],
                "password" : result.result.split(" ")[2]
            }
        else:
            result.result = {
                "type" : "cmd",
                "cmd" : cmd_output_fixer(result.result)
            }

        return result

    def analyze_result(self, cmd, result):

        model = self.llm_connection.get_model()
        ctx = self.llm_connection.get_context_size()

        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        CUTOFF_STEP = 128
        current_size = num_tokens_from_string(model, result)
        while current_size > (ctx + 512):
            cut_off = int(((current_size - (ctx + 512)) + CUTOFF_STEP)/2)
            result = result[cut_off:]
            current_size = num_tokens_from_string(model, result)

        result = self.create_and_ask_prompt_text('analyze_cmd.txt', cmd=cmd, resp=result, facts=self.state)
        return result

    def update_state(self, cmd, result):
        result = self.create_and_ask_prompt_text('update_state.txt', cmd=cmd, resp=result, facts=self.state)
        self.state = result.result
        return result

    def get_current_state(self):
        return self.state
    
    def create_and_ask_prompt_text(self, template_file, **params):
        template = Template(filename='templates/' + template_file)
        prompt = template.render(**params)
        tic = time.perf_counter()
        result, tok_query, tok_res = self.llm_connection.exec_query(self.llm_connection.get_model(), self.llm_connection.get_context_size(), prompt)
        toc = time.perf_counter()    
        return LLMResult(result, prompt, result, toc - tic, tok_query, tok_res)