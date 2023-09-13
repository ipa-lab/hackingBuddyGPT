import logging
import json
import time

from datetime import datetime
from mako.template import Template

class LLM:
    def __init__(self, llm_connection):
        self.connection = llm_connection

        # prepare logging
        self.log = logging.getLogger()
        filename = datetime.now().strftime('logs/run_%Y%m%d%m-%H%M.log')
        self.log.addHandler(logging.FileHandler(filename))
        self.get_openai_response = llm_connection

    # helper for generating and executing LLM prompts from a template
    def create_and_ask_prompt(self, template_file, log_prefix, **params):

        template = Template(filename='templates/' + template_file)
        prompt = template.render(**params)
        self.log.warning("[" + log_prefix + "-prompt] " + prompt)
        tic = time.perf_counter()
        result, tok_query, tok_res = self.get_openai_response(prompt)
        toc = time.perf_counter()
        self.log.warning("[" + log_prefix + "-answer] " + result)

        print("result: " + result)

        return json.loads(result), str(toc-tic), tok_query, tok_res
