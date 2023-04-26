class ResultHistory:
    def __init__(self):
        self.data = []

    def append(self, cmd, result):
        self.data.append({
            "cmd": cmd,
            "result": result
        })

    def dump(self):
        return self.data

