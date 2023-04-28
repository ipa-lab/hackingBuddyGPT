import logging

from colorama import Fore, Style
from datetime import datetime
from mako.template import Template

from llms.openai import get_openai_response

log = logging.getLogger()
filename = datetime.now().strftime('logs/run_%H_%M_%d_%m_%Y.log')
log.addHandler(logging.FileHandler(filename))

def output_log(self, kind, msg):
    print("[" + Fore.RED + kind + Style.RESET_ALL +"]: " + msg)
    self.log.warning("[" + kind + "] " + msg)

# helper for generating and executing LLM prompts from a template
def create_and_ask_prompt(template_file, log_prefix, **params):
    global logs

    template = Template(filename='templates/' + template_file)
    prompt = template.render(**params)
    logs.warning(log_prefix + "-prompt", prompt)
    result = get_openai_response(prompt)
    logs.warning(log_prefix + "-answer", result)
    return result