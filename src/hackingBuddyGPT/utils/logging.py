import datetime
from enum import Enum
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Optional, Union
import threading

from dataclasses_json.api import dataclass_json

from hackingBuddyGPT.utils import configurable, DbStorage, Console, LLMResult
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


@configurable("logger", "Logger")
@dataclass
class Logger:
    log_db: DbStorage
    console: Console
    tag: str = ""

    run: Run = field(init=False, default=None)

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: Optional[str] = None

    async def start_run(self, name: str, configuration: str):
        if self.run is not None:
            raise ValueError("Run already started")
        start_time = datetime.datetime.now()
        run_id = self.log_db.create_run(name, self.tag, start_time , configuration)
        self.run = Run(run_id, name, "", self.tag, start_time, None, configuration)

    async def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    async def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        section_id = self._last_section_id
        self._last_section_id += 1

        self.log_db.add_section(self.run.id, section_id, name, from_message, to_message, duration)

        return section_id

    async def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        self.log_db.add_section(self.run.id, section_id, name, from_message, self._last_message_id, duration)

    async def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    async def add_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        self.log_db.add_message(self.run.id, message_id, self._current_conversation, role, content, tokens_query, tokens_response, duration)
        self.console.print(Panel(content, title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role)))

        return message_id

    async def _add_or_update_message(self, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        self.log_db.add_or_update_message(self.run.id, message_id, conversation, role, content, tokens_query, tokens_response, duration)

    async def add_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: datetime.timedelta):
        self.console.print(Panel(
            Group(
                Panel(arguments, title="arguments"),
                Panel(result_text, title="result"),
            ),
            title=f"Tool Call: {function_name}"))
        self.log_db.add_tool_call(self.run.id, message_id, tool_call_id, function_name, arguments, result_text, duration)

    async def run_was_success(self):
        await self.status_message("Run finished successfully")
        self.log_db.run_was_success(self.run.id)

    async def run_was_failure(self, reason: str, details: Optional[str] = None):
        full_reason = reason + ("" if details is None else f": {details}")
        await self.status_message(f"Run failed: {full_reason}")
        self.log_db.run_was_failure(self.run.id, reason)

    async def status_message(self, message: str):
        await self.add_message("status", message, 0, 0, datetime.timedelta(0))

    async def system_message(self, message: str):
        await self.add_message("system", message, 0, 0, datetime.timedelta(0))

    async def call_response(self, llm_result: LLMResult) -> int:
        await self.system_message(llm_result.prompt)
        return await self.add_message("assistant", llm_result.answer, llm_result.tokens_query, llm_result.tokens_response, llm_result.duration)

    async def stream_message(self, role: str):
        message_id = self._last_message_id
        self._last_message_id += 1

        logger = MessageStreamLogger(self, message_id, self._current_conversation, role)
        await logger.init()
        return logger

    async def add_message_update(self, message_id: int, action: StreamAction, content: str):
        self.log_db.handle_message_update(self.run.id, message_id, action, content)


@configurable("logger", "Logger")
@dataclass
class RemoteLogger:
    console: Console
    log_server_address: str = "localhost:4444"

    tag: str = ""
    run: Run = field(init=False, default=None)

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: Optional[str] = None
    _upstream_websocket: ClientConnection = None
    _keepalive_thread: Optional[threading.Thread] = None
    _keepalive_stop_event: threading.Event = field(init=False, default_factory=threading.Event)

    def __del__(self):
        if self._upstream_websocket:
            self._upstream_websocket.close()
        if self._keepalive_thread:
            self._keepalive_stop_event.set()
            self._keepalive_thread.join()

    async def init_websocket(self):
        self._upstream_websocket = ws_connect(f"ws://{self.log_server_address}/ingress")  # TODO: we want to support wss at some point
        # self.start_keepalive()

    async def start_keepalive(self):
        self._keepalive_stop_event.clear()
        self._keepalive_thread = threading.Thread(target=self.keepalive)
        self._keepalive_thread.start()

    def keepalive(self):
        while not self._keepalive_stop_event.is_set():
            try:
                self._upstream_websocket.ping()
                self._upstream_websocket.pong()
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("Keepalive error:", e)
                self._keepalive_stop_event.set()
            time.sleep(5)

    async def send(self, type: MessageType, data: MessageData):
        self._upstream_websocket.send(ControlMessage(type, data).to_json())

    async def start_run(self, name: str, configuration: str, tag: Optional[str] = None, start_time: Optional[datetime.datetime] = None, end_time: Optional[datetime.datetime] = None):
        if self._upstream_websocket is None:
            await self.init_websocket()

        if self.run is not None:
            raise ValueError("Run already started")

        if tag is None:
            tag = self.tag

        if start_time is None:
            start_time = datetime.datetime.now()

        self.run = Run(None, name, None, tag, start_time, None, configuration)
        await self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    async def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        section_id = self._last_section_id
        self._last_section_id += 1

        section = Section(self.run.id, section_id, name, from_message, to_message, duration)
        await self.send(MessageType.SECTION, section)

        return section_id

    async def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        await self.send(MessageType.SECTION, Section(self.run.id, section_id, name, from_message, self._last_message_id, duration))

    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    async def add_message(self, role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        msg = Message(self.run.id, message_id, version=1, conversation=self._current_conversation, role=role, content=content, duration=duration, tokens_query=tokens_query, tokens_response=tokens_response)
        await self.send(MessageType.MESSAGE, msg)
        self.console.print(Panel(content, title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role)))

        return message_id

    async def _add_or_update_message(self, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        msg = Message(self.run.id, message_id, version=0, conversation=conversation, role=role, content=content, duration=duration, tokens_query=tokens_query, tokens_response=tokens_response)
        await self.send(MessageType.MESSAGE, msg)

    async def add_tool_call(self, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: datetime.timedelta):
        self.console.print(Panel(
            Group(
                Panel(arguments, title="arguments"),
                Panel(result_text, title="result"),
            ),
            title=f"Tool Call: {function_name}"))
        tc = ToolCall(self.run.id, message_id, tool_call_id, 0, function_name, arguments, "success", result_text, duration)
        await self.send(MessageType.TOOL_CALL, tc)

    async def run_was_success(self):
        await self.status_message("Run finished successfully")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = "success"
        await self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    async def run_was_failure(self, reason: str, details: Optional[str] = None):
        full_reason = reason + ("" if details is None else f": {details}")
        await self.status_message(f"Run failed: {full_reason}")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = reason
        await self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())

    async def status_message(self, message: str):
        await self.add_message("status", message, 0, 0, datetime.timedelta(0))

    async def system_message(self, message: str):
        await self.add_message("system", message, 0, 0, datetime.timedelta(0))

    async def call_response(self, llm_result: LLMResult) -> int:
        await self.system_message(llm_result.prompt)
        return await self.add_message("assistant", llm_result.answer, llm_result.tokens_query, llm_result.tokens_response, llm_result.duration)

    def stream_message(self, role: str):
        message_id = self._last_message_id
        self._last_message_id += 1

        return MessageStreamLogger(self, message_id, self._current_conversation, role)

    async def add_message_update(self, message_id: int, action: StreamAction, content: str):
        part = MessageStreamPart(id=None, run_id=self.run.id, message_id=message_id, action=action, content=content)
        await self.send(MessageType.MESSAGE_STREAM_PART, part)


@dataclass
class LogSectionContext:
    logger: Logger
    name: str
    from_message: int

    _section_id: int = 0

    async def __aenter__(self):
        self._start = datetime.datetime.now()
        self._section_id = await self.logger.log_section(self.name, self.from_message, None, datetime.timedelta(0))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.datetime.now() - self._start
        await self.logger.finalize_section(self._section_id, self.name, self.from_message, duration)


@dataclass
class LogConversationContext:
    logger: Logger
    with_section: bool
    conversation: str
    previous_conversation: Optional[str]

    _section: Optional[LogSectionContext] = None

    async def __aenter__(self):
        if self.with_section:
            self._section = LogSectionContext(self.logger, self.conversation, self.logger._last_message_id)
            await self._section.__aenter__()
        self.logger._current_conversation = self.conversation
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._section is not None:
            await self._section.__aexit__(exc_type, exc_val, exc_tb)
            del self._section
        self.logger._current_conversation = self.previous_conversation


@dataclass
class MessageStreamLogger:
    logger: Logger
    message_id: int
    conversation: Optional[str]
    role: str

    _completed: bool = False

    async def init(self):
        await self.logger._add_or_update_message(self.message_id, self.conversation, self.role, "", 0, 0, datetime.timedelta(0))

    def __del__(self):
        if not self._completed:
            print(f"streamed message was not finalized ({self.logger.run.id}, {self.message_id}), please make sure to call finalize() on MessageStreamLogger objects")

    async def append(self, content: str):
        if self._completed:
            raise ValueError("MessageStreamLogger already finalized")
        await self.logger.add_message_update(self.message_id, "append", content)

    async def finalize(self, tokens_query: int, tokens_response: int, duration: datetime.timedelta, overwrite_finished_message: Optional[str] = None):
        self._completed = True
        if overwrite_finished_message:
            await self.logger._add_or_update_message(self.message_id, self.conversation, self.role, overwrite_finished_message, tokens_query, tokens_response, duration)
        else:
            await self.logger._add_or_update_message(self.message_id, self.conversation, self.role, "", tokens_query, tokens_response, duration)
        return self.message_id


GlobalLocalLogger = Global(Transparent(Logger))
GlobalRemoteLogger = Global(Transparent(RemoteLogger))
GlobalLogger = GlobalRemoteLogger
