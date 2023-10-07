import time
import tiktoken
import typing

from db_storage import DbStorage
from dataclasses import dataclass
from mako.template import Template
from cmd_cleaner import cmd_output_fixer

@dataclass
class LLMResult:
    result: typing.Any
    prompt: str
    answer: str
    duration: float = 0
    tokens_query: int = 0
    tokens_response: int = 0


TPL_NEXT = Template(filename='templates/query_next_command.txt')
TPL_ANALYZE = Template(filename="templates/analyze_cmd.txt")
TPL_STATE = Template(filename="templates/update_state.txt")
    
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

        model = self.llm_connection.get_model()

        state_size = self.get_state_size(model)
        template_size = num_tokens_from_string(model, TPL_NEXT.source)

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size)
        # history = ''

        if self.target.os == "linux":
            target_user = "root"
        else:
            target_user = "Administrator"

        cmd = self.create_and_ask_prompt_text(TPL_NEXT, history=history, state=self.state, target=self.target, update_state=self.enable_update_state, target_user=target_user)
        cmd.result = cmd_output_fixer(cmd.result)
        return cmd

    def analyze_result(self, cmd, result):

        model = self.llm_connection.get_model()
        ctx = self.llm_connection.get_context_size()
        state_size = num_tokens_from_string(model, self.state)
        target_size = ctx - SAFETY_MARGIN - state_size 

        # ugly, but cut down result to fit context size
        result = trim_result_front(model, target_size, result)
        return self.create_and_ask_prompt_text(TPL_ANALYZE, cmd=cmd, resp=result, facts=self.state)

    def update_state(self, cmd, result):

        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        model = self.llm_connection.get_model()

        ctx = self.llm_connection.get_context_size()
        state_size = num_tokens_from_string(model, self.state)
        target_size = ctx - SAFETY_MARGIN - state_size
        result = trim_result_front(model, target_size, result)

        result = self.create_and_ask_prompt_text(TPL_STATE, cmd=cmd, resp=result, facts=self.state)
        self.state = result.result
        return result

    def get_current_state(self):
        return self.state
    
    def create_and_ask_prompt_text(self, template, **params):
        # prepare the prompt
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

STEP_CUT_TOKENS : int = 128
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
    cur_size = num_tokens_from_string(model, result)
    
    allowed = ctx_size - SAFETY_MARGIN - token_overhead
    return trim_result_front(model, allowed, result)

def wrap_it_for_llama(prompt):
    return f"""[INST]{prompt}[/INST]
"""


# trim it down if too large
STEP_CUT_TOKENS = 32

# this is ugly, but basically we only have an approximation how many tokens
# we are currently using. So we cannot just cut down to the desired size
# what we're doing is:
#   - take our current token count
#   - use the minimum of (current_count, desired count *2)
#     - this get's us roughly in the ballpark of the desired size
#     - as long as we assume that 2 * desired-count will always be larger
#       than the unschaerfe introduced by the string-.token conversion
#   - do a 'binary search' to cut-down to the desired size afterwards
#
# this should reduce the time needed to do the string->token conversion
# as this can be long-running if the LLM puts in a 'find /' output
def trim_result_front(model, target_size, result):
    cur_size = num_tokens_from_string(model, result)

    TARGET_SIZE_FACTOR = 3
    if cur_size > TARGET_SIZE_FACTOR * target_size:
        print(f"big step trim-down from {cur_size} to {2*target_size}")
        result = result[:TARGET_SIZE_FACTOR*target_size]
        cur_size = num_tokens_from_string(model, result)
   
    while cur_size > target_size:
        print(f"need to trim down from {cur_size} to {target_size}")
        diff = cur_size - target_size
        step = int((diff + STEP_CUT_TOKENS)/2)
        result = result[:-step]
        cur_size = num_tokens_from_string(model, result)

    return result
