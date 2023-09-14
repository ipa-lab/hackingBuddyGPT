import json
import time

from mako.template import Template
from helper import *

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
        state_size = num_tokens_from_string(self.state)

        next_cmd, diff, tok_query, tok_res = self.create_and_ask_prompt('query_next_command.txt', user=self.initial_user, password=self.initial_password, history=get_cmd_history(self.run_id, self.db, self.llm_connection.get_context_size()-state_size), state=self.state)
        
        return next_cmd, diff, tok_query, tok_res

    def analyze_result(self, cmd, result):
        resp_success, diff_2, tok_query, tok_resp = self.create_and_ask_prompt('successfull.txt', cmd=cmd, resp=result, facts=self.state)

        self.tmp_state = resp_success["facts"]

        return resp_success, diff_2, tok_query, tok_resp

    def update_state(self):
        self.state = "\n".join(map(lambda x: "- " + x, self.tmp_state))
        return self.state

    def get_current_state(self):
        return self.state
    
    def create_and_ask_prompt(self, template_file, **params):
        template = Template(filename='templates/' + template_file)
        prompt = template.render(**params)
        tic = time.perf_counter()
        result, tok_query, tok_res = self.llm_connection.exec_query(prompt)
        toc = time.perf_counter()
        print(str(result))
        return json.loads(result), str(toc-tic), tok_query, tok_res