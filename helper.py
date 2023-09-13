import os
import tiktoken

from db_storage import DbStorage
from rich.table import Table

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    model = os.getenv("MODEL")
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(string))

def get_history_table(run_id: int, db: DbStorage, round: int) -> Table:
    table = Table(show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Reason")

    for i in range(0, round+1):
        table.add_row(*db.get_round_data(run_id, i))

    return table

def get_cmd_history(run_id: int, db: DbStorage, limit: int) -> list[str]:
    result = []
    rest = limit

    # get commands from db
    cmds = db.get_cmd_history(run_id)

    for itm in reversed(cmds):
        size_cmd = num_tokens_from_string(itm[0])
        size_result = num_tokens_from_string(itm[1])
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