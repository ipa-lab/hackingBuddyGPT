import datetime
from enum import Enum
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Optional, Union
import threading

from dataclasses_json.api import dataclass_json

from hackingBuddyGPT.utils import Console, DbStorage, LLMResult, configurable, parameter
from hackingBuddyGPT.utils.db_storage.db_storage import StreamAction
from hackingBuddyGPT.utils.configurable import Global, Transparent
from rich.console import Group
from rich.panel import Panel
from websockets.sync.client import ClientConnection, connect as ws_connect

from hackingBuddyGPT.utils.db_storage.db_storage import Run, Section, Message, MessageStreamPart, ToolCall, ToolCallStreamPart


def log_section(name: str, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            with logger.section(name):
                return fun(self, *args, **kwargs)
        return inner
    return outer


def log_conversation(conversation: str, start_section: bool = False, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            with logger.conversation(conversation, start_section):
                return fun(self, *args, **kwargs)
        return inner
    return outer


MessageData = Union[Run, Section, Message, MessageStreamPart, ToolCall, ToolCallStreamPart]


class MessageType(str, Enum):
    MESSAGE_REQUEST = "MessageRequest"
    RUN = "Run"
    SECTION = "Section"
    MESSAGE = "Message"
    MESSAGE_STREAM_PART = "MessageStreamPart"
    TOOL_CALL = "ToolCall"
    TOOL_CALL_STREAM_PART = "ToolCallStreamPart"

    def get_class(self):
        return {
            "Run": Run,
            "Section": Section,
            "Message": Message,
            "MessageStreamPart": MessageStreamPart,
            "ToolCall": ToolCall,
            "ToolCallStreamPart": ToolCallStreamPart,
        }[self.value]


@dataclass_json
@dataclass
class ControlMessage:
    type: MessageType
    data: MessageData

    @classmethod
    def from_dict(cls, data):
        type_ = MessageType(data['type'])
        data_class = type_.get_class()
        data_instance = data_class.from_dict(data['data'])
        return cls(type=type_, data=data_instance)


@configurable("local_logger", "Local Logger")
@dataclass
class LocalLogger:
    log_db: DbStorage
    console: Console

    tag: str = parameter(desc="Tag for your current run", default="")

    run: Run = field(init=False, default=None)  # field and not a parameter, since this can not be user configured

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: Optional[str] = None

    def start_run(self, name: str, configuration: str):
        if self.run is not None:
            raise ValueError("Run already started")
        start_time = datetime.datetime.now()
        run_id = self.log_db.create_run(name, self.tag, start_time , configuration)
        self.run = Run(run_id, name, "", self.tag, start_time, None, configuration)

    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        section_id = self._last_section_id
        self._last_section_id += 1

        self.log_db.add_section(self.run.id, section_id, name, from_message, to_message, duration)

        return section_id

    def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        self.log_db.add_section(self.run.id, section_id, name, from_message, self._last_message_id, duration)

    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    def add_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        self.log_db.add_message(self.run.id, message_id, self._current_conversation, role, content, tokens_query, tokens_response, duration)
        self.console.print(Panel(content, title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role)))

        return message_id

    def _add_or_update_message(self, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        self.log_db.add_or_update_message(self.run.id, message_id, conversation, role, content, tokens_query, tokens_response, duration)

    def add_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: datetime.timedelta):
        self.console.print(Panel(
            Group(
                Panel(arguments, title="arguments"),
                Panel(result_text, title="result"),
            ),
            title=f"Tool Call: {function_name}"))
        self.log_db.add_tool_call(self.run.id, message_id, tool_call_id, function_name, arguments, result_text, duration)

    def run_was_success(self):
        self.status_message("Run finished successfully")
        self.log_db.run_was_success(self.run.id)

    def run_was_failure(self, reason: str, details: Optional[str] = None):
        full_reason = reason + ("" if details is None else f": {details}")
        self.status_message(f"Run failed: {full_reason}")
        self.log_db.run_was_failure(self.run.id, reason)

    def status_message(self, message: str):
        self.add_message("status", message, 0, 0, datetime.timedelta(0))

    def system_message(self, message: str):
        self.add_message("system", message, 0, 0, datetime.timedelta(0))

    def call_response(self, llm_result: LLMResult) -> int:
        self.system_message(llm_result.prompt)
        return self.add_message("assistant", llm_result.answer, llm_result.tokens_query, llm_result.tokens_response, llm_result.duration)

    def stream_message(self, role: str):
        message_id = self._last_message_id
        self._last_message_id += 1

        return MessageStreamLogger(self, message_id, self._current_conversation, role)

    def add_message_update(self, message_id: int, action: StreamAction, content: str):
        self.log_db.handle_message_update(self.run.id, message_id, action, content)


@configurable("remote_logger", "Remote Logger")
@dataclass
class RemoteLogger:
    console: Console
    log_server_address: str = parameter(desc="address:port of the log server to be used", default="localhost:4444")

    tag: str = parameter(desc="Tag for your current run", default="")

    run: Run = field(init=False, default=None)  # field and not a parameter, since this can not be user configured

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: Optional[str] = None
    _upstream_websocket: ClientConnection = None

    def __del__(self):
        if self._upstream_websocket:
            self._upstream_websocket.close()

    def init_websocket(self):
        self._upstream_websocket = ws_connect(f"ws://{self.log_server_address}/ingress")  # TODO: we want to support wss at some point

    def send(self, type: MessageType, data: MessageData):
        self._upstream_websocket.send(ControlMessage(type, data).to_json())

    def start_run(self, name: str, configuration: str, tag: Optional[str] = None, start_time: Optional[datetime.datetime] = None, end_time: Optional[datetime.datetime] = None):
        if self._upstream_websocket is None:
            self.init_websocket()

        if self.run is not None:
            raise ValueError("Run already started")

        if tag is None:
            tag = self.tag

        if start_time is None:
            start_time = datetime.datetime.now()

        self.run = Run(None, name, None, tag, start_time, None, configuration)
        self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        section_id = self._last_section_id
        self._last_section_id += 1

        section = Section(self.run.id, section_id, name, from_message, to_message, duration)
        self.send(MessageType.SECTION, section)

        return section_id

    def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        self.send(MessageType.SECTION, Section(self.run.id, section_id, name, from_message, self._last_message_id, duration))

    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    def add_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        msg = Message(self.run.id, message_id, version=1, conversation=self._current_conversation, role=role, content=content, duration=duration, tokens_query=tokens_query, tokens_response=tokens_response)
        self.send(MessageType.MESSAGE, msg)
        self.console.print(Panel(content, title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role)))

        return message_id

    def _add_or_update_message(self, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        msg = Message(self.run.id, message_id, version=0, conversation=conversation, role=role, content=content, duration=duration, tokens_query=tokens_query, tokens_response=tokens_response)
        self.send(MessageType.MESSAGE, msg)

    def add_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: datetime.timedelta):
        self.console.print(Panel(
            Group(
                Panel(arguments, title="arguments"),
                Panel(result_text, title="result"),
            ),
            title=f"Tool Call: {function_name}"))
        tc = ToolCall(self.run.id, message_id, tool_call_id, 0, function_name, arguments, "success", result_text, duration)
        self.send(MessageType.TOOL_CALL, tc)

    def run_was_success(self):
        self.status_message("Run finished successfully")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = "success"
        self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    def run_was_failure(self, reason: str, details: Optional[str] = None):
        full_reason = reason + ("" if details is None else f": {details}")
        self.status_message(f"Run failed: {full_reason}")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = reason
        self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    def status_message(self, message: str):
        self.add_message("status", message, 0, 0, datetime.timedelta(0))

    def system_message(self, message: str):
        self.add_message("system", message, 0, 0, datetime.timedelta(0))

    def call_response(self, llm_result: LLMResult) -> int:
        self.system_message(llm_result.prompt)
        return self.add_message("assistant", llm_result.answer, llm_result.tokens_query, llm_result.tokens_response, llm_result.duration)

    def stream_message(self, role: str):
        message_id = self._last_message_id
        self._last_message_id += 1

        return MessageStreamLogger(self, message_id, self._current_conversation, role)

    def add_message_update(self, message_id: int, action: StreamAction, content: str):
        part = MessageStreamPart(id=None, run_id=self.run.id, message_id=message_id, action=action, content=content)
        self.send(MessageType.MESSAGE_STREAM_PART, part)


GlobalLocalLogger = Global(LocalLogger)
GlobalRemoteLogger = Global(RemoteLogger)
Logger = Union[GlobalRemoteLogger, GlobalLocalLogger]
log_param = parameter(desc="choice of logging backend", default="local_logger")


@dataclass
class LogSectionContext:
    logger: Logger
    name: str
    from_message: int

    _section_id: int = 0

    def __enter__(self):
        self._start = datetime.datetime.now()
        self._section_id = self.logger.log_section(self.name, self.from_message, None, datetime.timedelta(0))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.datetime.now() - self._start
        self.logger.finalize_section(self._section_id, self.name, self.from_message, duration)


@dataclass
class LogConversationContext:
    logger: Logger
    with_section: bool
    conversation: str
    previous_conversation: Optional[str]

    _section: Optional[LogSectionContext] = None

    def __enter__(self):
        if self.with_section:
            self._section = LogSectionContext(self.logger, self.conversation, self.logger._last_message_id)
            self._section.__enter__()
        self.logger._current_conversation = self.conversation
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._section is not None:
            self._section.__exit__(exc_type, exc_val, exc_tb)
            del self._section
        self.logger._current_conversation = self.previous_conversation


@dataclass
class MessageStreamLogger:
    logger: Logger
    message_id: int
    conversation: Optional[str]
    role: str

    _completed: bool = False

    def __post_init__(self):
        self.logger._add_or_update_message(self.message_id, self.conversation, self.role, "", 0, 0, datetime.timedelta(0))

    def __del__(self):
        if not self._completed:
            print(f"streamed message was not finalized ({self.logger.run.id}, {self.message_id}), please make sure to call finalize() on MessageStreamLogger objects")
            self.finalize(0, 0, datetime.timedelta(0))

    def append(self, content: str):
        if self._completed:
            raise ValueError("MessageStreamLogger already finalized")
        self.logger.add_message_update(self.message_id, "append", content)

    def finalize(self, tokens_query: int, tokens_response: int, duration: datetime.timedelta, overwrite_finished_message: Optional[str] = None):
        self._completed = True
        self.logger._add_or_update_message(self.message_id, self.conversation, self.role, "", tokens_query, tokens_response, duration)
        return self.message_id
