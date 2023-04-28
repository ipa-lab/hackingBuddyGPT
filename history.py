import tiktoken

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(string))


class ResultHistory:
    def __init__(self):
        self.data = []

    def append(self, cmd, result):
        self.data.append({
            "cmd": cmd,
            "result": result
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