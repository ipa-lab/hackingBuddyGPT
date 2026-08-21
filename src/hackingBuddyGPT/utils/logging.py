"""
Run logging.

A single :class:`JsonlLogger` writes one OpenTelemetry/GenAI JSONL file per run (see
:mod:`hackingBuddyGPT.utils.log_storage`) and mirrors each event to the rich console. It exposes
the same method surface the rest of the codebase already calls (``start_run``, ``section``,
``conversation``, ``call_response``, ``add_tool_call``, ``status_message`` / ``system_message`` /
``limit_message``, ``run_was_success`` / ``run_was_failure``), so use-cases and agents are
unaffected by the switch away from the old SQLite/remote backends.
"""

import datetime
from dataclasses import dataclass, field
from functools import wraps
from typing import Optional

from rich.console import Group
from rich.panel import Panel

from hackingBuddyGPT.utils import Console, LLMResult, configurable, parameter
from hackingBuddyGPT.utils.configurable import Global
from hackingBuddyGPT.utils.log_storage import (
    GEN_AI_CONVERSATION_ID,
    GEN_AI_INPUT_MESSAGES,
    GEN_AI_OPERATION_NAME,
    GEN_AI_OUTPUT_MESSAGES,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_FINISH_REASONS,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_TOOL_CALL_ARGUMENTS,
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_NAME,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_USAGE_REASONING_OUTPUT_TOKENS,
    HB_COST_USD,
    HB_MESSAGE_ROLE,
    HB_REASONING,
    HB_RUN_CONFIGURATION,
    HB_RUN_NAME,
    HB_RUN_STATE,
    HB_RUN_TAG,
    HB_SECTION_CONVERSATION,
    HB_SECTION_NAME,
    HB_TOOL_RESULT,
    HB_USAGE_DETAILS,
    KIND_CLIENT,
    KIND_INTERNAL,
    OP_CHAT,
    OP_EXECUTE_TOOL,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_UNSET,
    Span,
    SpanWriter,
    as_timedelta,
    message,
    text_part,
)


def log_section(name: str, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        async def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            async with logger.section(name):
                return await fun(self, *args, **kwargs)

        return inner

    return outer


def log_conversation(conversation: str, start_section: bool = False, logger_field_name: str = "log"):
    def outer(fun):
        @wraps(fun)
        async def inner(self, *args, **kwargs):
            logger = getattr(self, logger_field_name)
            async with logger.conversation(conversation, start_section):
                return await fun(self, *args, **kwargs)

        return inner

    return outer


@configurable("jsonl_logger", "Logs each run to a single OpenTelemetry/GenAI JSONL file under logs/")
@dataclass
class JsonlLogger:
    console: Console

    log_dir: str = parameter(desc="directory for the per-run JSONL log files", default="logs")
    tag: str = parameter(desc="Tag for your current run", default="")

    _writer: SpanWriter = field(init=False, default=None)
    _run_span: Span = field(init=False, default=None)
    _stack: list = field(init=False, default_factory=list)
    _next_message_id: int = field(init=False, default=0)
    _message_spans: dict = field(init=False, default_factory=dict)
    _current_conversation: Optional[str] = field(init=False, default=None)

    # --- span plumbing -------------------------------------------------------

    @property
    def _parent_id(self) -> Optional[str]:
        return self._stack[-1].span_id if self._stack else None

    def _emit(
        self,
        name: str,
        kind: str,
        attributes: dict,
        start: datetime.datetime,
        end: datetime.datetime,
        parent_span_id: Optional[str] = ...,
        status_code: str = STATUS_OK,
        status_message: str = "",
    ) -> Span:
        span = Span(
            trace_id=self._writer.trace_id,
            span_id=self._writer.new_id(8),
            parent_span_id=self._parent_id if parent_span_id is ... else parent_span_id,
            name=name,
            kind=kind,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            attributes=attributes,
            status={"code": status_code, "message": status_message},
        )
        self._writer.write(span)
        return span

    # --- run lifecycle -------------------------------------------------------

    async def start_run(self, name: str, configuration: str):
        if self._writer is not None:
            raise ValueError("Run already started")

        started_at = datetime.datetime.now()
        self._writer = SpanWriter(self.log_dir)
        trace_id = self._writer.open(started_at)

        self._run_span = Span(
            trace_id=trace_id,
            span_id=self._writer.new_id(8),
            parent_span_id=None,
            name=name,
            kind=KIND_INTERNAL,
            start_time=started_at.isoformat(),
            end_time=None,
            attributes={
                HB_RUN_NAME: name,
                HB_RUN_TAG: self.tag,
                HB_RUN_CONFIGURATION: configuration,
                GEN_AI_CONVERSATION_ID: trace_id,
            },
            status={"code": STATUS_UNSET, "message": ""},
        )
        self._stack = [self._run_span]
        # written immediately (end_time=None) so the file and its config exist even on a crash;
        # the same span_id is re-emitted at run end with the terminal status.
        self._writer.write(self._run_span)
        self.console.log(f"[green]logging run to {self._writer.path}")

    def _finish_run(self, status_code: str, state: str):
        self._run_span.end_time = datetime.datetime.now().isoformat()
        self._run_span.status = {"code": status_code, "message": state}
        self._run_span.attributes[HB_RUN_STATE] = state
        self._writer.write(self._run_span)
        self._writer.close()

    async def run_was_success(self) -> int:
        message_id = await self.status_message("Run finished successfully")
        self._finish_run(STATUS_OK, "got root")
        return message_id

    async def run_was_failure(self, reason: str, details: Optional[str] = None) -> int:
        full_reason = (reason if reason is not None else "") + ("" if details is None else f": {details}")
        message_id = await self.status_message(f"Run failed: {full_reason}")
        self._finish_run(STATUS_ERROR, reason if reason else "failure")
        return message_id

    # --- sections / conversations -------------------------------------------

    def section(self, name: str) -> "LogSectionContext":
        return LogSectionContext(self, name)

    def conversation(self, conversation: str, start_section: bool = False) -> "LogConversationContext":
        return LogConversationContext(self, start_section, conversation, self._current_conversation)

    def _open_section(self, name: str) -> Span:
        span = Span(
            trace_id=self._writer.trace_id,
            span_id=self._writer.new_id(8),
            parent_span_id=self._parent_id,
            name=name,
            kind=KIND_INTERNAL,
            start_time=datetime.datetime.now().isoformat(),
            end_time=None,
            attributes={HB_SECTION_NAME: name}
            | ({HB_SECTION_CONVERSATION: self._current_conversation} if self._current_conversation else {}),
            status={"code": STATUS_UNSET, "message": ""},
        )
        self._stack.append(span)
        return span

    def _close_section(self, span: Span, failed: bool):
        span.end_time = datetime.datetime.now().isoformat()
        span.status = {"code": STATUS_ERROR if failed else STATUS_OK, "message": ""}
        # pop everything down to and including this span, tolerating imbalance
        if span in self._stack:
            while self._stack and self._stack[-1] is not span:
                self._stack.pop()
            self._stack.pop()
        # emitted at close (after its children) — readers link by parent_span_id, not file order
        self._writer.write(span)

    # --- messages ------------------------------------------------------------

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
        message_id = self._next_message_id
        self._next_message_id += 1

        end = datetime.datetime.now()
        start = end - as_timedelta(duration)

        attributes = {
            HB_MESSAGE_ROLE: role,
            GEN_AI_OUTPUT_MESSAGES: [message(role, [text_part(content)])],
        }
        if reasoning:
            attributes[HB_REASONING] = reasoning
        if tokens_query:
            attributes[GEN_AI_USAGE_INPUT_TOKENS] = tokens_query
        if tokens_response:
            attributes[GEN_AI_USAGE_OUTPUT_TOKENS] = tokens_response
        if cost:
            attributes[HB_COST_USD] = cost

        span = self._emit("message", KIND_INTERNAL, attributes, start, end)
        self._message_spans[message_id] = span.span_id

        self.console.print(
            Panel(
                content,
                title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + role),
            )
        )
        return message_id

    async def status_message(self, message_text: str) -> int:
        return await self.add_message("status", message_text, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def limit_message(self, message_text: str) -> int:
        return await self.add_message("limit", message_text, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def system_message(self, message_text: str) -> int:
        return await self.add_message("system", message_text, "", 0, 0, 0, "", 0, datetime.timedelta(0))

    async def call_response(self, llm_result: LLMResult) -> int:
        """Log one LLM turn as a single ``chat`` span carrying input + output messages and usage."""
        message_id = self._next_message_id
        self._next_message_id += 1

        end = datetime.datetime.now()
        start = end - as_timedelta(llm_result.duration)

        model = getattr(llm_result, "model", "") or ""
        provider = getattr(llm_result, "provider", "") or ""
        finish_reason = getattr(llm_result, "finish_reason", "") or ""

        attributes = {
            GEN_AI_OPERATION_NAME: OP_CHAT,
            GEN_AI_INPUT_MESSAGES: [message("user", [text_part(llm_result.prompt)])],
            GEN_AI_OUTPUT_MESSAGES: [
                message(
                    "assistant",
                    [text_part(llm_result.answer)],
                    finish_reason=finish_reason or None,
                )
            ],
            GEN_AI_USAGE_INPUT_TOKENS: llm_result.tokens_query,
            GEN_AI_USAGE_OUTPUT_TOKENS: llm_result.tokens_response,
        }
        if model:
            attributes[GEN_AI_REQUEST_MODEL] = model
            attributes[GEN_AI_RESPONSE_MODEL] = model
        if provider:
            attributes[GEN_AI_PROVIDER_NAME] = provider
        if finish_reason:
            attributes[GEN_AI_RESPONSE_FINISH_REASONS] = [finish_reason]
        if llm_result.tokens_reasoning:
            attributes[GEN_AI_USAGE_REASONING_OUTPUT_TOKENS] = llm_result.tokens_reasoning
        if llm_result.reasoning:
            attributes[HB_REASONING] = llm_result.reasoning
        if llm_result.cost:
            attributes[HB_COST_USD] = llm_result.cost
        if llm_result.usage_details:
            attributes[HB_USAGE_DETAILS] = llm_result.usage_details

        span = self._emit(f"chat {model}" if model else OP_CHAT, KIND_CLIENT, attributes, start, end)
        self._message_spans[message_id] = span.span_id

        self.console.print(
            Panel(
                llm_result.answer,
                title=(("" if self._current_conversation is None else f"{self._current_conversation} - ") + "assistant"),
            )
        )
        return message_id

    # --- tool calls ----------------------------------------------------------

    async def add_tool_call(
        self,
        message_id: int,
        tool_call_id: str,
        function_name: str,
        arguments: str,
        result_text: str,
        duration: datetime.timedelta,
    ):
        end = datetime.datetime.now()
        start = end - as_timedelta(duration)

        attributes = {
            GEN_AI_OPERATION_NAME: OP_EXECUTE_TOOL,
            GEN_AI_TOOL_NAME: function_name,
            GEN_AI_TOOL_CALL_ID: str(tool_call_id),
            GEN_AI_TOOL_CALL_ARGUMENTS: arguments,
            HB_TOOL_RESULT: result_text,
        }
        # a tool call is a child of the LLM span (message) that requested it
        parent = self._message_spans.get(message_id, self._parent_id)
        self._emit(
            f"execute_tool {function_name}" if function_name else OP_EXECUTE_TOOL,
            KIND_INTERNAL,
            attributes,
            start,
            end,
            parent_span_id=parent,
        )

        self.console.print(
            Panel(
                Group(
                    Panel(arguments, title="arguments"),
                    Panel(result_text, title="result"),
                ),
                title=f"Tool Call: {function_name}",
            )
        )


Logger = Global(JsonlLogger)
# kept for backwards compatibility as the default value of the injected `log` field; the value is
# ignored for a complex (non-Union) configurable type, which is instantiated directly.
log_param = parameter(desc="run logging configuration", default=None)


@dataclass
class LogSectionContext:
    logger: JsonlLogger
    name: str

    _span: Span = None

    async def __aenter__(self):
        self._span = self.logger._open_section(self.name)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger._close_section(self._span, failed=exc_type is not None)


@dataclass
class LogConversationContext:
    logger: JsonlLogger
    with_section: bool
    conversation: str
    previous_conversation: Optional[str]

    _section: Optional[LogSectionContext] = None

    async def __aenter__(self):
        if self.with_section:
            self._section = LogSectionContext(self.logger, self.conversation)
            await self._section.__aenter__()
        self.logger._current_conversation = self.conversation
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._section is not None:
            await self._section.__aexit__(exc_type, exc_val, exc_tb)
            self._section = None
        self.logger._current_conversation = self.previous_conversation
