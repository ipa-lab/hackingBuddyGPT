"""Characterisation test for the strategy (CommandStrategy) priv-esc run loop.

The only test that exercised this loop (``integration_minimal_test.py``) is skipped — it imports a
pre-PR-#141 module layout that no longer exists. This pins the *current* ``CommandStrategy.run``
behaviour (drive scripted commands, detect the connector's verified root proof, return ``True``)
before the run-loop unification (converge onto ``AutonomousUseCase.run`` + ``Limits``) touches it.

A fake SSH connection maps commands to canned output and a fake LLM replays a fixed command
sequence, so the loop runs deterministically to a root escalation.
"""

import asyncio
import tempfile
import unittest
from typing import Tuple

from hackingBuddyGPT.usecases.priv_esc.linux_privesc import PrivEscLinux
from hackingBuddyGPT.usecases.priv_esc.minimal_linux_privesc import MinimalPrivEscLinux
from hackingBuddyGPT.utils.connectors.local_shell import LocalShellConnection
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.llm_util import LLM, LLMResult
from hackingBuddyGPT.utils.logging import JsonlLogger

# The winning command whose fake connection reports a verified proof.
ROOT_CMD = "sudo su"
_RESULTS = {
    "id": "uid=1001(lowpriv) gid=1001(lowpriv) groups=1001(lowpriv)",
    "sudo -l": "Sorry, user lowpriv may not run sudo.",
    ROOT_CMD: "root shell entered",
}


class FakeSSHConnection:
    username: str = "lowpriv"
    password: str = "toomanysecrets"
    hostname: str = "host"
    banner: str = ""
    root_verified: bool = False

    async def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        out = _RESULTS.get(cmd, "")
        self.root_verified = cmd == ROOT_CMD
        return (out, "", 0) if out else ("", "Command not found", 1)

    async def test_credential(self, username: str, password: str):
        return None

    def new_with(self, **kwargs):
        return self


class FakeLLM(LLM):
    model: str = "fake_model"
    context_size: int = 4096

    def __init__(self, responses):
        self._responses = responses
        self._counter = 0

    def get_response(self, prompt, *, capabilities=None, **kwargs) -> LLMResult:
        response = self._responses[self._counter]
        self._counter += 1
        return LLMResult(result=response, prompt="prompt", answer=response, reasoning="")

    def encode(self, query) -> list[int]:
        return [0]


def _log():
    return JsonlLogger(console=Console(), log_dir=tempfile.mkdtemp())


def _render_prompt(agent):
    agent.init()
    return agent._template.render(**(agent._template_params | {"history": [], "capabilities": ""}))


class TestStrategyPrivEscRunLoop(unittest.TestCase):
    def test_ssh_prompt_describes_both_success_paths(self):
        agent = MinimalPrivEscLinux(conn=FakeSSHConnection(), llm=FakeLLM([]), log=_log())
        prompt = _render_prompt(agent)

        self.assertIn("in the persistent shell or authenticate as that user with 'test_credential'", prompt)

    def test_local_prompt_does_not_offer_credential_check(self):
        local_agent = PrivEscLinux(conn=LocalShellConnection(tmux_session="unused"), llm=FakeLLM([]), log=_log())
        self.assertNotIn("test_credential", _render_prompt(local_agent))

    def test_linux_privesc_reaches_root(self):
        responses = ["id", "sudo -l", ROOT_CMD]
        agent = PrivEscLinux(
            conn=FakeSSHConnection(),
            llm=FakeLLM(responses),
            log=_log(),
            max_turns=len(responses),
        )
        agent.init()
        result = asyncio.run(agent.run({}))
        self.assertTrue(result)

    def test_minimal_linux_privesc_reaches_root(self):
        responses = ["id", ROOT_CMD]
        agent = MinimalPrivEscLinux(
            conn=FakeSSHConnection(),
            llm=FakeLLM(responses),
            log=_log(),
            max_turns=len(responses),
        )
        agent.init()
        result = asyncio.run(agent.run({}))
        self.assertTrue(result)

    def test_no_root_within_budget_is_failure(self):
        # Never escalates; the loop must exhaust its turn budget and report not-solved.
        responses = ["id", "sudo -l"]
        agent = MinimalPrivEscLinux(
            conn=FakeSSHConnection(),
            llm=FakeLLM(responses),
            log=_log(),
            max_turns=len(responses),
        )
        agent.init()
        result = asyncio.run(agent.run({}))
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
