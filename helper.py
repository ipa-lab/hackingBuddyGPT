import tiktoken

from db_storage import DbStorage
from rich.table import Table

def num_tokens_from_string(model: str, string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(string))

def get_history_table(run_id: int, db: DbStorage, round: int) -> Table:
    table = Table(title="Executed Command History", show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    table.add_column("ThinkingTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Reason")
    table.add_column("StateTime", style="dim")
    table.add_column("StateTokens", style="dim")

    for i in range(0, round+1):
        table.add_row(*db.get_round_data(run_id, i))

    return table

# return a list with cmd/result pairs, trimmed to context_size
def get_cmd_history(model: str, run_id: int, db: DbStorage, limit: int) -> list[str]:
    result = []
    rest = limit

    # get commands from db
    cmds = db.get_cmd_history(run_id)

    for itm in reversed(cmds):
        size_cmd = num_tokens_from_string(model, itm[0])
        size_result = num_tokens_from_string(model, itm[1])
        size = size_cmd + size_result

        if size <= rest:
            result.append(itm)
            rest -= size
        else:
            # if theres a bit space left, fill that up with parts of the last item
            if (rest - size_cmd) >= 200:
                result.append({
                    "cmd" : itm[0],
                    "result" : itm[1][:(rest-size_cmd-2)] + ".."
                })
            return list(reversed(result))
    return list(reversed(result))

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

def remove_wrapping_characters(cmd, wrappers):
    if cmd[0] == cmd[-1] and cmd[0] in wrappers:
        print("will remove a wrapper from: " + cmd)
        return remove_wrapping_characters(cmd[1:-1], wrappers)
    return cmd

# often the LLM produces a wrapped command
def cmd_output_fixer(cmd):
    cmd = remove_wrapping_characters(cmd, "`'\"")

    if cmd.startswith("$ "):
        cmd = cmd[2:]
    
    return cmd