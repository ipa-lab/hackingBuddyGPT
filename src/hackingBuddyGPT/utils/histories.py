import abc

# TODO: make the configuration for different histories easier
# Logger = Union[GlobalRemoteLogger, GlobalLocalLogger]
# log_param = parameter(desc="choice of logging backend", default="local_logger")
#@dataclass
#class Agent(ABC):
#    log: Logger = log_param

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

    def get_text_representation(self) -> str:
        return "\n".join(f"${cmd}\n {result}\n" for cmd, result in self.history)
    
class HistoryCmdOnly(History):

    history = []

    def __init__(self):
        self.history = []

    def append(self, cmd: str, result: str):
        self.history.append(cmd)

    def get_text_representation(self) -> str:
        return "\n".join(f"${cmd}\n" for cmd in self.history)