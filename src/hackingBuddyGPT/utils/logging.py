import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Optional, Union, override

from dataclasses_json.api import dataclass_json
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from rich.console import Group
from rich.panel import Panel
from websockets.sync.client import ClientConnection
from websockets.sync.client import connect as ws_connect

from hackingBuddyGPT.utils import Console, DbStorage, LLMResult, configurable, parameter
from hackingBuddyGPT.utils.configurable import Global
from hackingBuddyGPT.utils.db_storage.db_storage import (
    Message,
    MessageStreamPart,
    Run,
    Section,
    StreamAction,
    ToolCall,
    ToolCallStreamPart,
)


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
        type_ = MessageType(data["type"])
        data_class = type_.get_class()
        data_instance = data_class.from_dict(data["data"])
        return cls(type=type_, data=data_instance)


class ALogger(ABC):
    @abstractmethod
    async def start_run(self, name: str, configuration: str):
        pass

    @abstractmethod
    def section(self, name: str) -> "LogSectionContext":
        pass

    @abstractmethod
    async def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta) -> int:
        pass

    @abstractmethod
    async def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        pass

    @abstractmethod
    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        pass

    @abstractmethod
    async def add_message(
        self,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ) -> int:
        pass

    @abstractmethod
    async def _add_or_update_message(
        self,
        message_id: int,
        conversation: str | None,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ):
        pass

    @abstractmethod
    async def add_tool_call(
        self,
        message_id: int,
        tool_call_id: str,
        function_name: str,
        arguments: str,
        result_text: str,
        duration: datetime.timedelta,
    ):
        pass

    @abstractmethod
    async def run_was_success(self) -> int:
        pass

    @abstractmethod
    async def run_was_failure(self, reason: str, details: Optional[str] = None) -> int:
        pass

    async def status_message(self, message: str) -> int:
        return await self.add_message("status", message, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def limit_message(self, message: str) -> int:
        return await self.add_message("limit", message, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def system_message(self, message: str) -> int:
        return await self.add_message("system", message, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def call_response(self, llm_result: LLMResult) -> int:
        _ = await self.system_message(llm_result.prompt)
        return await self.add_message(
            "assistant",
            llm_result.answer,
            llm_result.reasoning,
            llm_result.tokens_query,
            llm_result.tokens_response,
            llm_result.tokens_reasoning,
            llm_result.usage_details,
            llm_result.cost,
            llm_result.duration,
        )

    @abstractmethod
    async def stream_message(self, role: str) -> "MessageStreamLogger":
        pass

    async def stream_message_from(
        self, role: str, stream: Iterable[ChoiceDelta | LLMResult]
    ) -> tuple[int, LLMResult] | None:
        log_stream = await self.stream_message(role)
        return await log_stream.consume(stream)

    @abstractmethod
    async def add_message_update(
        self, message_id: int, action: StreamAction, content: str, reasoning: str | None = None
    ):
        pass


@configurable("local_logger", "Local Logger")
@dataclass
class LocalLogger(ALogger):
    log_db: DbStorage
    console: Console

    tag: str = parameter(desc="Tag for your current run", default="")

    run: Run = field(init=False, default=None)  # field and not a parameter, since this can not be user configured

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: str | None = None

    @override
    async def start_run(self, name: str, configuration: str):
        if self.run is not None:
            raise ValueError("Run already started")
        start_time = datetime.datetime.now()
        run_id = self.log_db.create_run(name, self.tag, start_time, configuration)
        self.run = Run(run_id, name, "", self.tag, start_time, None, configuration)

    @override
    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    @override
    async def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta) -> int:
        section_id = self._last_section_id
        self._last_section_id += 1

        self.log_db.add_section(self.run.id, section_id, name, from_message, to_message, duration)

        return section_id

    @override
    async def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        self.log_db.add_section(self.run.id, section_id, name, from_message, self._last_message_id, duration)

    @override
    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    @override
    async def add_message(
        self,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        self.log_db.add_message(
            self.run.id,
            message_id,
            self._current_conversation,
            role,
            content,
            reasoning,
            tokens_query,
            tokens_response,
            tokens_reasoning,
            usage_details,
            cost,
            duration,
        )
        self.console.print(
            Panel(
                content,
                title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role),
            )
        )

        return message_id

    @override
    async def _add_or_update_message(
        self,
        message_id: int,
        conversation: str | None,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ):
        self.log_db.add_or_update_message(
            self.run.id,
            message_id,
            conversation,
            role,
            content,
            reasoning,
            tokens_query,
            tokens_response,
            tokens_reasoning,
            usage_details,
            cost,
            duration,
        )

    @override
    async def add_tool_call(
        self,
        message_id: int,
        tool_call_id: str,
        function_name: str,
        arguments: str,
        result_text: str,
        duration: datetime.timedelta,
    ):
        self.console.print(
            Panel(
                Group(
                    Panel(arguments, title="arguments"),
                    Panel(result_text, title="result"),
                ),
                title=f"Tool Call: {function_name}",
            )
        )
        self.log_db.add_tool_call(
            self.run.id, message_id, tool_call_id, function_name, arguments, result_text, duration
        )

    @override
    async def run_was_success(self) -> int:
        message_id = await self.status_message("Run finished successfully")
        self.log_db.run_was_success(self.run.id)
        return message_id

    @override
    async def run_was_failure(self, reason: str, details: Optional[str] = None) -> int:
        full_reason = reason + ("" if details is None else f": {details}")
        message_id = await self.status_message(f"Run failed: {full_reason}")
        self.log_db.run_was_failure(self.run.id, reason)
        return message_id

    @override
    async def stream_message(self, role: str) -> "MessageStreamLogger":
        message_id = self._last_message_id
        self._last_message_id += 1
        logger = MessageStreamLogger(self, message_id, self._current_conversation, role, local_output=True)
        await logger.init()
        return logger

    @override
    async def add_message_update(
        self, message_id: int, action: StreamAction, content: str, reasoning: Optional[str] = None
    ):
        self.log_db.handle_message_update(self.run.id, message_id, action, content, reasoning)


@configurable("remote_logger", "Remote Logger")
@dataclass
class RemoteLogger(ALogger):
    console: Console
    log_server_address: str = parameter(desc="address:port of the log server to be used", default="localhost:4444")
    local_output: bool = parameter(desc="Whether to output to local console", default=True)

    tag: str = parameter(desc="Tag for your current run", default="")

    run: Run = field(init=False, default=None)  # field and not a parameter, since this can not be user configured

    _last_message_id: int = 0
    _last_section_id: int = 0
    _current_conversation: str | None = None
    _upstream_websocket: ClientConnection = None

    def __del__(self):
        if self._upstream_websocket:
            self._upstream_websocket.close()

    async def init_websocket(self):
        self._upstream_websocket = ws_connect(
            f"ws://{self.log_server_address}/ingress"
        )  # TODO: we want to support wss at some point

    async def send(self, type: MessageType, data: MessageData):
        self._upstream_websocket.send(ControlMessage(type, data).to_json())

    @override
    async def start_run(
        self,
        name: str,
        configuration: str,
        tag: str | None = None,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
    ):
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

    @override
    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name, self._last_message_id)

    @override
    async def log_section(self, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        section_id = self._last_section_id
        self._last_section_id += 1

        section = Section(self.run.id, section_id, name, from_message, to_message, duration)
        await self.send(MessageType.SECTION, section)

        return section_id

    @override
    async def finalize_section(self, section_id: int, name: str, from_message: int, duration: datetime.timedelta):
        await self.send(
            MessageType.SECTION, Section(self.run.id, section_id, name, from_message, self._last_message_id, duration)
        )

    @override
    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    @override
    async def add_message(
        self,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ) -> int:
        message_id = self._last_message_id
        self._last_message_id += 1

        msg = Message(
            self.run.id,
            message_id,
            version=1,
            conversation=self._current_conversation,
            role=role,
            content=content,
            reasoning=reasoning,
            duration=duration,
            tokens_query=tokens_query,
            tokens_response=tokens_response,
            tokens_reasoning=tokens_reasoning,
            usage_details=usage_details,
            cost=cost,
        )
        await self.send(MessageType.MESSAGE, msg)
        if self.local_output:
            self.console.print(
                Panel(
                    content,
                    title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role),
                )
            )

        return message_id

    @override
    async def _add_or_update_message(
        self,
        message_id: int,
        conversation: str | None,
        role: str,
        content: str,
        reasoning: str,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
    ):
        msg = Message(
            self.run.id,
            message_id,
            version=0,
            conversation=conversation,
            role=role,
            content=content,
            reasoning=reasoning,
            duration=duration,
            tokens_query=tokens_query,
            tokens_response=tokens_response,
            tokens_reasoning=tokens_reasoning,
            usage_details=usage_details,
            cost=cost,
        )
        await self.send(MessageType.MESSAGE, msg)

    @override
    async def add_tool_call(
        self,
        message_id: int,
        tool_call_id: str,
        function_name: str,
        arguments: str,
        result_text: str,
        duration: datetime.timedelta,
    ):
        if self.local_output:
            self.console.print(
                Panel(
                    Group(
                        Panel(arguments, title="arguments"),
                        Panel(result_text, title="result"),
                    ),
                    title=f"Tool Call: {function_name}",
                )
            )
        tc = ToolCall(
            self.run.id, message_id, tool_call_id, 0, function_name, arguments, "success", result_text, duration
        )
        await self.send(MessageType.TOOL_CALL, tc)

    @override
    async def run_was_success(self) -> int:
        message_id = await self.status_message("Run finished successfully")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = "success"
        await self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())
        return message_id

    @override
    async def run_was_failure(self, reason: str, details: Optional[str] = None) -> int:
        full_reason = (reason if reason is not None else "") + ("" if details is None else f": {details}")
        message_id = await self.status_message(f"Run failed: {full_reason}")
        self.run.stopped_at = datetime.datetime.now()
        self.run.state = reason
        await self.send(MessageType.RUN, self.run)
        self.run = Run.from_json(self._upstream_websocket.recv())
        return message_id

    @override
    async def stream_message(self, role: str) -> "MessageStreamLogger":
        message_id = self._last_message_id
        self._last_message_id += 1

        logger = MessageStreamLogger(self, message_id, self._current_conversation, role, local_output=self.local_output)
        await logger.init()
        return logger

    @override
    async def add_message_update(
        self, message_id: int, action: StreamAction, content: str, reasoning: str | None = None
    ):
        part = MessageStreamPart(
            id=None, run_id=self.run.id, message_id=message_id, action=action, content=content, reasoning=reasoning
        )
        await self.send(MessageType.MESSAGE_STREAM_PART, part)


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
    local_output: bool

    _completed: bool = False
    _started_reasoning: bool = False
    _printed_role: bool = False

    async def init(self):
        await self.logger._add_or_update_message(
            self.message_id, self.conversation, self.role, "", "", 0, 0, 0, "", 0, datetime.timedelta(0)
        )

    def __del__(self):
        if not self._completed:
            print(
                f"streamed message was not finalized ({self.logger.run.id}, {self.message_id}), please make sure to call finalize() on MessageStreamLogger objects"
            )
            # TODO: re-add? self.finalize(0, 0, 0, datetime.timedelta(0))

    async def consume(self, stream: Iterable[ChoiceDelta | LLMResult]) -> tuple[int, LLMResult] | None:
        result: LLMResult | None = None

        for delta in stream:
            if isinstance(delta, LLMResult):
                result = delta
                break
            if delta.content is not None:
                await self.append(
                    delta.content, delta.reasoning if hasattr(delta, "reasoning") else None
                )  # TODO: reasoning is theoretically not defined on the model

        if result is None:
            await self.logger.status_message("No result from the LLM")
            return None

        message_id = await self.finalize(
            result.tokens_query,
            result.tokens_response,
            result.tokens_reasoning,
            result.usage_details,
            result.cost,
            result.duration,
            overwrite_finished_message=result.answer,
        )

        return message_id, result

    async def append(self, content: str, reasoning: str | None = None):
        if self._completed:
            raise ValueError("MessageStreamLogger already finalized")
        if self.local_output:
            if reasoning is not None:
                if self._printed_role:
                    pass  # TODO: all bets are off
                elif not self._started_reasoning:
                    self.logger.console.print("\n\n[bold blue]REASONING:[/bold blue]")
                    self._started_reasoning = True
                self.logger.console.print(reasoning, end="")

            if content is not None and len(content) > 0:
                if not self._printed_role:
                    self.logger.console.print("\n\n[bold blue]ASSISTANT:[/bold blue]")
                    self._printed_role = True
                self.logger.console.print(content, end="")

        await self.logger.add_message_update(self.message_id, "append", content, reasoning)

    async def finalize(
        self,
        tokens_query: int,
        tokens_response: int,
        tokens_reasoning: int,
        usage_details: str,
        cost: float,
        duration: datetime.timedelta,
        overwrite_finished_message: str | None = None,
    ):
        self._completed = True
        if overwrite_finished_message:
            await self.logger._add_or_update_message(
                self.message_id,
                self.conversation,
                self.role,
                overwrite_finished_message,
                "",
                tokens_query,
                tokens_response,
                tokens_reasoning,
                usage_details,
                cost,
                duration,
            )
        else:
            await self.logger._add_or_update_message(
                self.message_id,
                self.conversation,
                self.role,
                "",
                "",
                tokens_query,
                tokens_response,
                tokens_reasoning,
                usage_details,
                cost,
                duration,
            )

        if self.local_output:
            self.logger.console.print()

        return self.message_id
