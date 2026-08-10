"""
Per-run logging storage.

Every started use-case writes a single append-only file ``logs/log-<timestamp>.jsonl`` (the
timestamp is the run start time). Each line is one completed OpenTelemetry span, serialized as a
small OTLP-compatible JSON subset and annotated with the GenAI semantic conventions
(``gen_ai.*``). LLM prompts/completions are stored as structured message *parts*, a shape that is
simultaneously OTel's ``gen_ai.input.messages``/``gen_ai.output.messages`` schema and the OWASP
Agent Observability Standard (AOS) ``Message``/``Part`` schema.

This module owns only the record model (``Span``), the attribute-key vocabulary, the small
message/part builders, and the append-only ``SpanWriter``. The reading/aggregation side used by
the CLI tools lives in :mod:`hackingBuddyGPT.analysis.log_model`.
"""

import datetime
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

# --- OpenTelemetry GenAI semantic-convention attribute keys ---
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_USAGE_REASONING_OUTPUT_TOKENS = "gen_ai.usage.reasoning.output_tokens"
GEN_AI_INPUT_MESSAGES = "gen_ai.input.messages"
GEN_AI_OUTPUT_MESSAGES = "gen_ai.output.messages"
GEN_AI_CONVERSATION_ID = "gen_ai.conversation.id"
GEN_AI_TOOL_NAME = "gen_ai.tool.name"
GEN_AI_TOOL_CALL_ID = "gen_ai.tool.call.id"
GEN_AI_TOOL_CALL_ARGUMENTS = "gen_ai.tool.call.arguments"

# --- project-specific attribute keys (things OTel/GenAI has no key for) ---
HB_RUN_NAME = "hackingbuddygpt.run.name"
HB_RUN_TAG = "hackingbuddygpt.run.tag"
HB_RUN_CONFIGURATION = "hackingbuddygpt.run.configuration"
HB_RUN_STATE = "hackingbuddygpt.run.state"
HB_COST_USD = "hackingbuddygpt.cost.usd"
HB_USAGE_DETAILS = "hackingbuddygpt.usage_details"
HB_REASONING = "hackingbuddygpt.reasoning"
HB_MESSAGE_ROLE = "hackingbuddygpt.message.role"
HB_TOOL_RESULT = "hackingbuddygpt.tool.result"
HB_SECTION_NAME = "hackingbuddygpt.section.name"
HB_SECTION_CONVERSATION = "hackingbuddygpt.section.conversation"

# well-known gen_ai.operation.name values
OP_CHAT = "chat"
OP_EXECUTE_TOOL = "execute_tool"

# span status codes (OTel StatusCode)
STATUS_UNSET = "UNSET"
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"

# span kinds (OTel SpanKind)
KIND_INTERNAL = "INTERNAL"
KIND_CLIENT = "CLIENT"


def iso_now() -> str:
    return datetime.datetime.now().isoformat()


def as_timedelta(duration: Union[datetime.timedelta, int, float, None]) -> datetime.timedelta:
    """Coerce a duration that may be a timedelta or a raw number of seconds (some call sites pass 0)."""
    if isinstance(duration, datetime.timedelta):
        return duration
    return datetime.timedelta(seconds=float(duration or 0))


def text_part(content: str) -> dict[str, Any]:
    """A message part, per OTel gen_ai / OWASP AOS ``TextPart`` (``kind``/``type`` == text)."""
    return {"type": "text", "content": content}


def message(role: str, parts: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    """An OTel gen_ai / AOS message object: a role plus an ordered list of content parts."""
    msg: dict[str, Any] = {"role": role, "parts": parts}
    for key, value in extra.items():
        if value is not None:
            msg[key] = value
    return msg


@dataclass
class Span:
    """One completed span, an OTLP-compatible JSON subset (ISO timestamps for readability)."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: str
    start_time: str
    end_time: Optional[str]
    attributes: dict[str, Any] = field(default_factory=dict)
    status: dict[str, str] = field(default_factory=lambda: {"code": STATUS_UNSET, "message": ""})

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class SpanWriter:
    """Owns the per-run JSONL file and hands out trace/span ids. Append-only, flushed per line."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.path: Optional[str] = None
        self.trace_id: Optional[str] = None
        self._file = None

    def open(self, started_at: datetime.datetime) -> str:
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        base = f"log-{started_at.strftime('%Y%m%d-%H%M%S')}"
        path = os.path.join(self.log_dir, f"{base}.jsonl")
        # guard against two runs starting within the same second
        suffix = 1
        while os.path.exists(path):
            path = os.path.join(self.log_dir, f"{base}-{suffix}.jsonl")
            suffix += 1
        self.path = path
        self._file = open(path, "w", encoding="utf-8")
        self.trace_id = self.new_id(16)
        return self.trace_id

    @staticmethod
    def new_id(n_bytes: int = 8) -> str:
        return secrets.token_hex(n_bytes)

    def write(self, span: Span) -> None:
        self._file.write(span.to_json_line() + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
