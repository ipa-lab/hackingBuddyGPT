import tiktoken
import os

from rich.table import Table

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    model = os.getenv("MODEL")
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(string))


class ResultHistory:
    def __init__(self):
        self.data = []

    def append(self, think_time, cmd_type, cmd, result, success, reasoning):
        self.data.append({
            "cmd": cmd,
            "result": result,
            "think_time": think_time,
            "cmd_type": cmd_type,
            "success": success,
            "reasoning": reasoning
        })

    def get_full_history(self):
        return self.data

    # only retrieve recent parts. We need this as prompts only allow
    # for maximum token length. We currently do this in a quite stupid
    # whay which could be optimized in the future
    def get_history(self, limit=3072):
        result = []
        rest = limit

        for itm in reversed(self.data):
            size_cmd = num_tokens_from_string(itm["cmd"])
            size_result = num_tokens_from_string(itm["result"])
            size = size_cmd + size_result

            if size <= rest:
                result.append(itm)
                rest -= size
            else:
                # if theres a bit space left, fill that up with parts of the last item
                if (rest - size_cmd) >= 200:
                    result.append({
                        "cmd" : itm["cmd"],
                        "result" : itm["result"][:(rest-size_cmd-2)] + ".."
                    })
                return list(reversed(result))
        return list(reversed(result))

    def create_history_table(self):
        table = Table(show_header=True, show_lines=True)
        table.add_column("Type", style="dim", width=7)
        table.add_column("ThinkTime", style="dim")
        table.add_column("To_Execute")
        table.add_column("Resp. Size", justify="right")
        table.add_column("success?", width=8)
        table.add_column("reason")

        for itm in self.data:
            table.add_row(itm["cmd_type"], itm["think_time"], itm["cmd"], str(len(itm["result"])), itm["success"], itm["reasoning"])

        return table