import abc

class History(abc.ABC):
    @abc.abstractmethod
    def append(self, cmd:str, result:str):
        pass

    @abc.abstractmethod
    def get_text_representation(self) -> str:
        pass

class HistoryNone(History):
    def append(self, cmd: str, result: str):
        pass

    def get_text_representation(self) -> str:
        return ""

class HistoryFull(History):

    history = []

    def __init__(self):
        self.history = []

    def append(self, cmd: str, result: str):
        self.history.append((cmd, result))

    # TODO: implement size limiter
    def get_text_representation(self) -> str:
        return "\n".join(f"${cmd}\n {result}\n" for cmd, result in self.history)
    
class HistoryCmdOnly(History):

    history = []

    def __init__(self):
        self.history = []

    def append(self, cmd: str, result: str):
        self.history.append(cmd)

    # TODO: implement size limiter
    def get_text_representation(self) -> str:
        return "\n".join(f"${cmd}\n" for cmd in self.history)