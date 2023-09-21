import time
import tiktoken
import typing

from db_storage import DbStorage
from dataclasses import dataclass
from mako.template import Template

@dataclass
class LLMResult:
    result: typing.Any
    prompt: str
    answer: str
    duration: float = 0
    tokens_query: int = 0
    tokens_response: int = 0

class LLMWithState:
    def __init__(self, run_id, llm_connection, history, config):
        self.llm_connection = llm_connection
        self.target = config.target
        self.db = history
        self.run_id = run_id
        self.enable_update_state = config.enable_update_state
        self.state = f"""
- this is a {self.target.os} system
- your low privilege user credentials are {self.target.user}:{self.target.password}
"""

    def get_state_size(self, model):
        if self.enable_update_state:
            return num_tokens_from_string(model, self.state)
        else:
            return 0

    def get_next_cmd(self):

        template_file = 'query_next_command.txt'
        model = self.llm_connection.get_model()

        state_size = self.get_state_size(model)

        template = Template(filename='templates/' + template_file)
        template_size = num_tokens_from_string(model, template.source)

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size)

        if self.target.os == "linux":
            target_user = "root"
        else:
            target_user = "Administrator"

        return self.create_and_ask_prompt_text(template_file, history=history, state=self.state, target=self.target, update_state=self.enable_update_state, target_user=target_user)

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
        # prepare the prompt
        template = Template(filename='templates/' + template_file)
        prompt = template.render(**params)

        if not self.llm_connection.get_model().startswith("gpt-"):
            prompt = wrap_it_for_llama(prompt)

        # and execute it
        tic = time.perf_counter()
        result, tok_query, tok_res = self.llm_connection.exec_query(self.llm_connection.get_model(), self.llm_connection.get_context_size(), prompt)
        toc = time.perf_counter()
    
        return LLMResult(result, prompt, result, toc - tic, tok_query, tok_res)
    
def num_tokens_from_string(model: str, string: str) -> int:
    """Returns the number of tokens in a text string."""

    # I know this is crappy for all non-openAI models but sadly this
    # has to be good enough for now
    if model.startswith("gpt-"):
        encoding = tiktoken.encoding_for_model(model)
    else:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(string))

STEP_CUT_TOKENS : int = 32
SAFETY_MARGIN : int = 128

# create the command history. Initially create the full command history, then
# try to trim it down
def get_cmd_history_v3(model: str, ctx_size: int, run_id: int, db: DbStorage, token_overhead: int) -> str:
    result: str = ""

    # get commands from db
    cmds = db.get_cmd_history(run_id)

    # create the full history
    for itm in cmds:
        result = result + '$ ' + itm[0] + "\n" + itm[1]

    # trim it down if too large
    cur_size = num_tokens_from_string(model, result) + token_overhead + SAFETY_MARGIN
        
    while cur_size > ctx_size:
        diff = cur_size - ctx_size
        step = int((diff + STEP_CUT_TOKENS)/2)
        result = result[:-step]
        cur_size = num_tokens_from_string(model, result) + token_overhead + SAFETY_MARGIN
    
    return result

def wrap_it_for_llama(prompt):
    return f"""### System:
you are a concise but helful learning tool that aids students trying to find security vulnerabilities

### User:
{prompt}

### Assistant:"""