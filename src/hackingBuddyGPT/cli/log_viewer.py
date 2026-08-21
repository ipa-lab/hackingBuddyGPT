"""
CLI: re-render a single per-run JSONL log to the terminal.

    hackingbuddygpt-log-view logs/log-<timestamp>.jsonl

Spans are de-duplicated by id (so the run span's initial + final lines collapse) and replayed in
start-time order, which reconstructs the run as it happened even though section spans are written
at their close.
"""

import argparse
from collections import defaultdict

from rich.console import Console, Group
from rich.panel import Panel

from hackingBuddyGPT.analysis.log_model import load_spans
from hackingBuddyGPT.utils.log_storage import (
    GEN_AI_INPUT_MESSAGES,
    GEN_AI_OPERATION_NAME,
    GEN_AI_OUTPUT_MESSAGES,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_TOOL_CALL_ARGUMENTS,
    GEN_AI_TOOL_NAME,
    HB_COST_USD,
    HB_MESSAGE_ROLE,
    HB_RUN_CONFIGURATION,
    HB_RUN_STATE,
    HB_RUN_TAG,
    HB_SECTION_NAME,
    HB_TOOL_RESULT,
    OP_CHAT,
    OP_EXECUTE_TOOL,
)


def _messages_to_text(messages) -> str:
    lines = []
    for msg in messages or []:
        for part in msg.get("parts", []):
            if part.get("type") == "text":
                lines.append(part.get("content", ""))
    return "\n".join(lines)


def _render_span(span: dict, console: Console) -> None:
    attrs = span.get("attributes", {})
    op = attrs.get(GEN_AI_OPERATION_NAME)

    if span.get("parent_span_id") is None:
        info = {
            "name": span.get("name", ""),
            "tag": attrs.get(HB_RUN_TAG, ""),
            "state": attrs.get(HB_RUN_STATE, span.get("status", {}).get("message", "in progress")),
            "configuration": attrs.get(HB_RUN_CONFIGURATION, ""),
        }
        console.print(Panel("\n".join(f"{k}: {v}" for k, v in info.items()), title="Run"))
    elif op == OP_CHAT:
        model = attrs.get(GEN_AI_REQUEST_MODEL, "")
        cost = attrs.get(HB_COST_USD)
        prompt = _messages_to_text(attrs.get(GEN_AI_INPUT_MESSAGES))
        answer = _messages_to_text(attrs.get(GEN_AI_OUTPUT_MESSAGES))
        title = f"LLM call: {model}" + (f"  (${cost:.4f})" if cost else "")
        console.print(Panel(Group(Panel(prompt, title="prompt"), Panel(answer, title="answer")), title=title))
    elif op == OP_EXECUTE_TOOL:
        console.print(
            Panel(
                Group(
                    Panel(attrs.get(GEN_AI_TOOL_CALL_ARGUMENTS, ""), title="arguments"),
                    Panel(attrs.get(HB_TOOL_RESULT, ""), title="result"),
                ),
                title=f"Tool call: {attrs.get(GEN_AI_TOOL_NAME, '')}",
            )
        )
    elif HB_SECTION_NAME in attrs:
        console.rule(span.get("name", ""))
    elif HB_MESSAGE_ROLE in attrs:
        content = _messages_to_text(attrs.get(GEN_AI_OUTPUT_MESSAGES))
        console.print(Panel(content, title=attrs.get(HB_MESSAGE_ROLE, "message")))


def render(path: str, console: Console) -> None:
    """Replay a run by walking the span tree (parent -> child), siblings in start-time order."""
    by_id = {span["span_id"]: span for span in load_spans(path)}  # collapses the run span's two lines

    children = defaultdict(list)
    root = None
    for span in by_id.values():
        parent = span.get("parent_span_id")
        children[parent].append(span)
        if parent is None:
            root = span
    for siblings in children.values():
        siblings.sort(key=lambda s: s.get("start_time") or "")

    seen = set()

    def walk(span: dict) -> None:
        if span["span_id"] in seen:
            return
        seen.add(span["span_id"])
        _render_span(span, console)
        for child in children.get(span["span_id"], []):
            walk(child)

    if root is not None:
        walk(root)
    # render any spans orphaned by a crash (parent never written) in start-time order
    for span in sorted(by_id.values(), key=lambda s: s.get("start_time") or ""):
        walk(span)


def main():
    parser = argparse.ArgumentParser(description="Replay a hackingBuddyGPT per-run JSONL log to the terminal.")
    parser.add_argument("input", help="path to a logs/log-<timestamp>.jsonl file")
    args = parser.parse_args()

    console = Console()
    render(args.input, console)


if __name__ == "__main__":
    main()
