import json
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

class LLMWithState:
    def __init__(self, run_id, llm_connection, history, initial_user, initial_password):
        self.llm_connection = llm_connection
        self.initial_user = initial_user
        self.initial_password = initial_password
        self.db = history
        self.run_id = run_id
        self.state = """
- this is a linux system
- your low privilege user credentials are lowpriv:trustno1
"""

    def get_next_cmd(self):

        template_file = 'query_next_command.txt'
        model = self.llm_connection.get_model()

        state_size = num_tokens_from_string(model, self.state)

        template = Template(filename='templates/' + template_file)
        template_size = num_tokens_from_string(model, template.source)

        commands = "\n".join(map(lambda x: f'- ${x}', list(set(map(lambda x: x[0], self.db.get_cmd_history(self.run_id))))))

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size+num_tokens_from_string(model, str(commands)))

        return self.create_and_ask_prompt(template_file, user=self.initial_user, password=self.initial_password, history=history, state=self.state, commands=commands)

    def analyze_result(self, cmd, result):
        result = self.create_and_ask_prompt('successfull.txt', cmd=cmd, resp=result, facts=self.state)

        self.tmp_state = result.result["facts"]
        return result

    def update_state(self):
        self.state = "\n".join(map(lambda x: "- " + x, self.tmp_state))
        return LLMResult(self.state, '', '', 0, 0, 0)

    def get_current_state(self):
        return self.state
    
    def create_and_ask_prompt(self, template_file, **params):
        template = Template(filename='templates/' + template_file)
        prompt = template.render(**params)
        tic = time.perf_counter()
        print("query:" + prompt)
        result, tok_query, tok_res = self.llm_connection.exec_query(self.llm_connection.get_model(), self.llm_connection.get_context_size(), prompt)
        print("result: " + result)
        toc = time.perf_counter()
        try:
            json_answer = json.loads(result)
        except Exception as e:
            print("there as an exception with JSON parsing: " + str(e))
            print("debug[the plain result]: " + str(result))
    
        return LLMResult(json_answer, prompt, result, toc - tic, tok_query, tok_res)