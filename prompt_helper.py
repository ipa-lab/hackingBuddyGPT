import logging
import json

from colorama import Fore, Style
from datetime import datetime
from mako.template import Template

from llms.openai_rest import get_openai_response

log = logging.getLogger()
filename = datetime.now().strftime('logs/run_%Y%m%d%m-%H%M.log')
log.addHandler(logging.FileHandler(filename))

def output_log(kind, msg):
    print("[" + Fore.RED + kind + Style.RESET_ALL +"]: " + msg)
    log.warning("[" + kind + "] " + msg)

# helper for generating and executing LLM prompts from a template
def create_and_ask_prompt(template_file, log_prefix, **params):
    global logs

    template = Template(filename='templates/' + template_file)
    prompt = template.render(**params)
    #output_log(log_prefix + "-prompt", prompt)
    result = get_openai_response(prompt)
    #output_log(log_prefix + "-answer", result)

    return json.loads(result)
