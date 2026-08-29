"""Tests for the ``task_solved`` fix in the tool-calling priv-esc use-case.

Covers the two coordinated pieces of the fix:

1. ``Limits`` scores an explicit ``complete()`` (what a verified ``task_solved`` triggers) as a
   success even when it happens on the final allowed round, instead of clobbering it with a
   "Reached maximum rounds" failure reason.
2. ``task_solved`` verifies the escalation against the live session before accepting it — via the
   persistent shell's identity or a proven root credential — so a hallucinated or conceding call
   cannot record a false success.
"""

import asyncio

from hackingBuddyGPT.usecases.priv_esc.minimal_linux_privesc_tool_calling import (
    MinimalToolCallPrivEscLinux,
    _RootWatchingRunCommand,
    _TrackingSSHTestCredential,
)
from hackingBuddyGPT.utils.limits import Limits, RunState
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL


# --------------------------------------------------------------------------------------------------
# Limits: an explicit completion wins over the resource-limit checks
# --------------------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------------------
# credential-based wins are tracked so task_solved can honour them
# --------------------------------------------------------------------------------------------------


class _FakeCredConn:
    """Minimal stand-in for the interactive connection's one-shot credential check."""

    def __init__(self, root_password):
        self.root_password = root_password

    async def test_credential(self, username, password):
        if username == "root" and password == self.root_password:
            return "uid=0(root) gid=0(root) groups=0(root)\n"
        return None  # auth failed


def test_tracking_credential_reports_only_on_root_login():
    seen = []
    cap = _TrackingSSHTestCredential(
        conn=_FakeCredConn("s3cret"), on_root_login=lambda u, p: seen.append((u, p))
    )
    assert cap.get_name() == "test_credential"

    wrong = asyncio.run(cap("root", "nope"))
    assert "wrong" in wrong.lower()
    assert seen == []  # a failed login must not mark the box solved

    ok = asyncio.run(cap("root", "s3cret"))
    assert ok == LOGIN_AS_ROOT_SUCCESSFUL
    assert seen == [("root", "s3cret")]


# --------------------------------------------------------------------------------------------------
# shell-identity verification used by task_solved
# --------------------------------------------------------------------------------------------------


class _FakeShellConn:
    """Interactive-connection stub: an ``id`` run publishes the session's uid/user."""

    def __init__(self, uid, user):
        self._uid, self._user = uid, user
        self.last_uid = None
        self.last_user = None

    async def run(self, cmd, *a, **k):
        self.last_uid, self.last_user = self._uid, self._user
        return (f"uid={self._uid}({self._user})", "", 0)


def _agent_with_conn(conn, target_user="root"):
    agent = object.__new__(MinimalToolCallPrivEscLinux)  # skip dataclass __init__/LLM wiring
    agent.conn = conn
    agent.target_user = target_user
    return agent


# --------------------------------------------------------------------------------------------------
# _RootWatchingRunCommand: flags genuinely-demonstrated root, ignores benign output
# --------------------------------------------------------------------------------------------------


class _ScriptedRunConn:
    """execute_bash_command connection stub: returns a canned (output, uid) per command."""

    hostname = "victim"

    def __init__(self, script):
        self._script = script  # cmd substring -> (output, session_uid)
        self.last_uid = 1000

    async def run(self, command, *a, **k):
        for key, (out, uid) in self._script.items():
            if key in command:
                self.last_uid = uid
                return (out, "", 0)
        self.last_uid = 1000
        return ("", "", 0)


def _run_and_watch(conn, command):
    fired = []
    cap = _RootWatchingRunCommand(conn=conn, on_root=lambda: fired.append(True))
    asyncio.run(cap(command))
    return bool(fired)


def test_root_watch_fires_on_uid0_output_one_shot():
    # SUID `bash -p -c id` / `sudo id`: session stays lowpriv but the output proves root
    conn = _ScriptedRunConn({"sudo id": ("uid=0(root) gid=0(root) groups=0(root)", 1000)})
    assert _run_and_watch(conn, "sudo id") is True


def test_root_watch_fires_on_euid0_output():
    conn = _ScriptedRunConn(
        {"bash -p": ("uid=1000(lowpriv) gid=1000(lowpriv) euid=0(root) groups=1000(lowpriv)", 1000)}
    )
    assert _run_and_watch(conn, "bash -p -c id") is True


def test_root_watch_fires_when_session_uid_is_zero():
    # `sudo su`: no telltale output, but the connector's in-session uid is now 0
    conn = _ScriptedRunConn({"sudo su": ("", 0)})
    assert _run_and_watch(conn, "sudo su") is True


def test_root_watch_ignores_benign_enumeration():
    conn = _ScriptedRunConn({"id": ("uid=1000(lowpriv) gid=1000(lowpriv) groups=1000(lowpriv)", 1000)})
    assert _run_and_watch(conn, "id") is False


def test_root_watch_ignores_output_without_root():
    conn = _ScriptedRunConn({"ls": ("backup.conf  shell.sh", 1000)})
    assert _run_and_watch(conn, "ls -la") is False


def test_shell_probe_detects_root():
    agent = _agent_with_conn(_FakeShellConn(0, "root"))
    assert asyncio.run(agent._shell_is_target_user()) is True


def test_shell_probe_rejects_lowpriv():
    agent = _agent_with_conn(_FakeShellConn(1000, "lowpriv"))
    assert asyncio.run(agent._shell_is_target_user()) is False


def test_shell_probe_honours_non_root_target_user():
    agent = _agent_with_conn(_FakeShellConn(1001, "deploy"), target_user="deploy")
    assert asyncio.run(agent._shell_is_target_user()) is True
