import asyncio
import datetime
import json

from hackingBuddyGPT.analysis.log_model import load_run
from hackingBuddyGPT.cli.log_viewer import render
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.llm_util import LLMResult
from hackingBuddyGPT.utils.logging import JsonlLogger


def _drive_run(log_dir: str) -> str:
    log = JsonlLogger(console=Console(), log_dir=log_dir, tag="test")

    async def run():
        await log.start_run("TestUseCase", json.dumps({"llm": {"model": "gpt-4o"}}))
        async with log.section("round 1"):
            result = LLMResult(
                result="ls",
                prompt="system prompt",
                answer="ls -la",
                reasoning="",
                duration=datetime.timedelta(seconds=1.5),
                tokens_query=100,
                tokens_response=20,
                tokens_reasoning=5,
                usage_details="{}",
                cost=0.001,
                model="gpt-4o",
                finish_reason="stop",
                provider="openai",
            )
            message_id = await log.call_response(result)
            # a call site that passes an int duration / tool_call_id, which must be tolerated
            await log.add_tool_call(message_id, tool_call_id=0, function_name="exec", arguments="ls", result_text="ok", duration=0)
        await log.run_was_success()
        return log._writer.path

    return asyncio.run(run())


def test_spans_are_valid_otel_genai(tmp_path):
    path = _drive_run(str(tmp_path))
    spans = [json.loads(line) for line in open(path) if line.strip()]

    for span in spans:
        assert span["trace_id"] and span["span_id"]
        assert "attributes" in span and "status" in span

    roots = [s for s in spans if s["parent_span_id"] is None]
    assert len(roots) == 2  # initial UNSET line + final authoritative line
    assert roots[0]["end_time"] is None and roots[0]["status"]["code"] == "UNSET"
    assert roots[-1]["status"]["code"] == "OK"

    chat = [s for s in spans if s["attributes"].get("gen_ai.operation.name") == "chat"]
    assert len(chat) == 1
    attrs = chat[0]["attributes"]
    assert attrs["gen_ai.request.model"] == "gpt-4o"
    assert attrs["gen_ai.usage.input_tokens"] == 100
    assert attrs["gen_ai.usage.output_tokens"] == 20
    assert attrs["gen_ai.input.messages"][0]["parts"][0]["content"] == "system prompt"

    tools = [s for s in spans if s["attributes"].get("gen_ai.operation.name") == "execute_tool"]
    assert len(tools) == 1
    # a tool call parents onto the LLM span that requested it
    assert tools[0]["parent_span_id"] == chat[0]["span_id"]


def test_load_run_aggregates(tmp_path):
    path = _drive_run(str(tmp_path))
    run = load_run(path)

    assert run.name == "TestUseCase"
    assert run.tag == "test"
    assert run.state == "got root"
    assert run.model == "gpt-4o"
    assert run.llm_calls == 1
    assert run.input_tokens == 100
    assert run.output_tokens == 20
    assert run.reasoning_tokens == 5
    assert abs(run.cost - 0.001) < 1e-9
    assert run.total_tool_calls == 1


def test_viewer_renders_without_error(tmp_path):
    path = _drive_run(str(tmp_path))
    # a non-terminal console still exercises the full render/dispatch path
    render(path, Console())
