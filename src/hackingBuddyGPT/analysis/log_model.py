"""
Reading side of the per-run JSONL logs.

``load_spans`` parses a ``logs/log-*.jsonl`` file into raw span dicts; ``load_run`` reduces one
file into a :class:`RunSummary` of the numbers the CLI tools report. Both the viewer and the
analyzer share this module so the parse rules live in exactly one place.
"""

import datetime
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

from hackingBuddyGPT.utils.log_storage import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_TOOL_NAME,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_USAGE_REASONING_OUTPUT_TOKENS,
    HB_COST_USD,
    HB_RUN_STATE,
    HB_RUN_TAG,
    OP_CHAT,
    OP_EXECUTE_TOOL,
)


def load_spans(path: str) -> list[dict[str, Any]]:
    spans = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def _parse_ts(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class RunSummary:
    path: str
    trace_id: str = ""
    name: str = ""
    tag: str = ""
    state: str = "in progress"
    model: str = ""
    start: Optional[datetime.datetime] = None
    end: Optional[datetime.datetime] = None
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost: float = 0.0
    tool_calls: Counter = field(default_factory=Counter)

    @property
    def duration_seconds(self) -> float:
        if self.start and self.end:
            return (self.end - self.start).total_seconds()
        return 0.0

    @property
    def total_tool_calls(self) -> int:
        return sum(self.tool_calls.values())


def load_run(path: str) -> RunSummary:
    spans = load_spans(path)
    summary = RunSummary(path=path)

    # the root run span is written twice (initial UNSET + final); the last one is authoritative
    roots = [s for s in spans if s.get("parent_span_id") is None]
    if roots:
        root = roots[-1]
        attrs = root.get("attributes", {})
        summary.trace_id = root.get("trace_id", "")
        summary.name = root.get("name", "")
        summary.tag = attrs.get(HB_RUN_TAG, "")
        summary.state = attrs.get(HB_RUN_STATE) or (root.get("status", {}).get("message")) or "in progress"
        summary.start = _parse_ts(roots[0].get("start_time"))
        summary.end = _parse_ts(root.get("end_time"))

    for span in spans:
        if span.get("parent_span_id") is None:
            continue
        attrs = span.get("attributes", {})
        op = attrs.get(GEN_AI_OPERATION_NAME)
        if op == OP_CHAT:
            summary.llm_calls += 1
            summary.input_tokens += attrs.get(GEN_AI_USAGE_INPUT_TOKENS, 0) or 0
            summary.output_tokens += attrs.get(GEN_AI_USAGE_OUTPUT_TOKENS, 0) or 0
            summary.reasoning_tokens += attrs.get(GEN_AI_USAGE_REASONING_OUTPUT_TOKENS, 0) or 0
            summary.cost += attrs.get(HB_COST_USD, 0.0) or 0.0
            if not summary.model:
                summary.model = attrs.get(GEN_AI_REQUEST_MODEL, "") or ""
        elif op == OP_EXECUTE_TOOL:
            summary.tool_calls[attrs.get(GEN_AI_TOOL_NAME, "") or "?"] += 1

    return summary
