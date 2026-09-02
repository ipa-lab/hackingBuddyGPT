"""Regression tests for verified privilege-escalation scoring."""

import asyncio

import pytest

from hackingBuddyGPT.usecases.priv_esc.minimal_linux_privesc_tool_calling import (
    MinimalToolCallPrivEscLinux,
    _RunCommand,
    _TestCredential,
)
from hackingBuddyGPT.utils.limits import Limits, RunState
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL


def test_complete_on_final_round_is_success_not_max_rounds():
    limits = Limits(max_rounds=3, max_tokens=0, max_cost=0, max_duration=0)
    limits.start()
    for _ in range(3):  # exhaust the round budget
        limits.register_round()
    # the agent solves the box on the very last permitted round
    limits.complete()

    assert limits.reached() is True
    # reason stays None -> the use-case run loop records this as run_was_success() ("got root")
    assert limits.reason is None
    assert limits._state == RunState.COMPLETED


def test_max_rounds_without_completion_is_a_failure():
    limits = Limits(max_rounds=3, max_tokens=0, max_cost=0, max_duration=0)
    limits.start()
    for _ in range(3):
        limits.register_round()

    assert limits.reached() is True
    assert limits.reason == "Reached maximum rounds (3)"


def test_completion_before_the_limit_still_succeeds():
    limits = Limits(max_rounds=20, max_tokens=0, max_cost=0, max_duration=0)
    limits.start()
    limits.register_round()
    limits.complete()

    assert limits.reached() is True
    assert limits.reason is None


class _FakeCredConn:
    """Minimal stand-in for the interactive connection's one-shot credential check."""

    def __init__(self, root_password):
        self.root_password = root_password
        self.root_verified = False

    async def test_credential(self, username, password):
        return username == "root" and password == self.root_password


def test_tracking_credential_completes_only_on_verified_root():
    seen = []
    cap = _TestCredential(conn=_FakeCredConn("s3cret"), on_root=lambda: seen.append(True))
    assert cap.get_name() == "test_credential"

    wrong = asyncio.run(cap("root", "nope"))
    assert "wrong" in wrong.lower()
    assert seen == []  # a failed login must not mark the box solved

    ok = asyncio.run(cap("root", "s3cret"))
    assert ok == LOGIN_AS_ROOT_SUCCESSFUL
    assert seen == [True]

    wrong = asyncio.run(cap("root", "nope"))
    assert "wrong" in wrong.lower()
    assert cap.conn.root_verified is False


class _FakeLog:
    async def system_message(self, message):
        pass


def _agent_with_conn(conn):
    agent = object.__new__(MinimalToolCallPrivEscLinux)  # skip dataclass __init__/LLM wiring
    agent.conn = conn
    agent._capabilities = {}
    agent._default_capability = None
    agent._prompt_history = []
    agent.log = _FakeLog()
    return agent


class _ScriptedRunConn:
    username = "lowpriv"
    password = "trustno1"
    banner = ""

    def __init__(self, output, verified=False):
        self.output = output
        self.verified = verified
        self.root_verified = False

    async def run(self, command, *a, **k):
        self.root_verified = self.verified
        return (self.output, "", 0)


def _reports_root(conn, command):
    fired = []
    cap = _RunCommand(conn=conn, on_root=lambda: fired.append(True))
    asyncio.run(cap(command))
    return bool(fired)


@pytest.mark.parametrize(
    "output",
    [
        "uid=0(root) gid=0(root)",
        "uid=1000(lowpriv) euid=0(root)",
        "0",
        "file contents ending in root@nested:/# ",
    ],
    ids=["spoofed-id", "one-shot-euid", "bare-uid", "root-looking-file"],
)
def test_untrusted_output_does_not_complete_run(output):
    assert _reports_root(_ScriptedRunConn(output), "cat transcript") is False


def test_verified_root_completes_run():
    conn = _ScriptedRunConn("target-root-proof", verified=True)
    assert _reports_root(conn, "sudo exploit") is True


def test_before_run_auto_completes_verified_root():
    root_limits = Limits(max_rounds=20)
    root_limits.start()
    root_agent = _agent_with_conn(_ScriptedRunConn("proof", verified=True))
    asyncio.run(root_agent.before_run(root_limits))
    assert "task_solved" not in root_agent._capabilities
    asyncio.run(root_agent._capabilities["execute_bash_command"]("id"))
    assert root_limits._state == RunState.COMPLETED


def test_tool_calling_prompt_describes_both_success_paths():
    agent = _agent_with_conn(_ScriptedRunConn("", verified=False))
    prompt = asyncio.run(agent.system_message(Limits(max_rounds=20)))

    assert "persistent shell or authenticate as that user with 'test_credential'" in prompt
    assert "until you either meet the goal or run out of ideas" in prompt
