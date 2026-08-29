"""Characterisation test for ``ChatAgent.perform_round`` (the shared tool-calling round).

This pins the exact behaviour of the loop that the whole native-tool-calling family relies on
(the ``web`` agents and ``MinimalToolCallPrivEscLinux``) BEFORE the capability-registry unification
(Option 2) and the shared ``run_tool_calling_turn`` extraction (Option 1) touch it. It must stay
green, unchanged, through both refactors — the byte-identical proof for that family.
"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from hackingBuddyGPT.usecases.agents import ChatAgent
from hackingBuddyGPT.utils.limits import Limits
from hackingBuddyGPT.utils.llm_util import tool_message


class _DummyChatAgent(ChatAgent):
    async def system_message(self, limits: Limits) -> str:
        return "SYS"


def _tool_call(call_id: str, name: str, arguments: str = "{}"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


class TestChatAgentPerformRound(unittest.TestCase):
    def _make_agent(self):
        llm = MagicMock()
        log = MagicMock()
        log.call_response = AsyncMock(return_value=7)
        log.add_tool_call = AsyncMock()
        log.limit_message = AsyncMock()
        log.status_message = AsyncMock()
        return _DummyChatAgent(llm=llm, log=log), llm, log

    def test_perform_round_appends_message_then_tool_results_in_order(self):
        agent, llm, log = self._make_agent()

        tc1 = _tool_call("c1", "X")
        tc2 = _tool_call("c2", "Y")
        message = SimpleNamespace(tool_calls=[tc1, tc2])
        result = SimpleNamespace(result=message, total_tokens=3, cost=0.5)
        llm.get_response = MagicMock(return_value=result)

        # Pin that execution flows through run_capability_json (the registry entry point).
        agent.run_capability_json = AsyncMock(
            side_effect=lambda mid, tcid, name, args: f"RES:{name}"
        )

        # All-zero limits -> str(limits) == "" so add_limits_message is a no-op (no user message added).
        limits = Limits(max_rounds=0, max_tokens=0, max_cost=0, max_duration=0)
        limits.start()

        asyncio.run(agent.perform_round(limits))

        # History: the assistant message, then the two tool results, in call order.
        self.assertEqual(
            agent._prompt_history,
            [message, tool_message("RES:X", "c1"), tool_message("RES:Y", "c2")],
        )

        # The model was asked once with the full history and the agent's capabilities.
        self.assertEqual(llm.get_response.call_count, 1)
        _args, _kwargs = llm.get_response.call_args
        self.assertIs(_args[0], agent._prompt_history)
        self.assertEqual(_kwargs, {"capabilities": agent._capabilities})

        # Both tool calls executed via run_capability_json, in order, with the tool-call fields.
        self.assertEqual(agent.run_capability_json.call_count, 2)
        self.assertEqual(
            [c.args for c in agent.run_capability_json.call_args_list],
            [(7, "c1", "X", "{}"), (7, "c2", "Y", "{}")],
        )

        # Limits bookkeeping: one message registered (tokens/cost), one round registered.
        self.assertEqual(limits.tokens, 3)
        self.assertEqual(limits.cost, 0.5)
        self.assertEqual(limits.rounds, 1)

    def test_perform_round_without_tool_calls_appends_only_message(self):
        agent, llm, log = self._make_agent()

        message = SimpleNamespace(tool_calls=None)
        result = SimpleNamespace(result=message, total_tokens=1, cost=0.0)
        llm.get_response = MagicMock(return_value=result)
        agent.run_capability_json = AsyncMock()

        limits = Limits(max_rounds=0, max_tokens=0, max_cost=0, max_duration=0)
        limits.start()

        asyncio.run(agent.perform_round(limits))

        self.assertEqual(agent._prompt_history, [message])
        agent.run_capability_json.assert_not_called()
        self.assertEqual(limits.rounds, 1)


if __name__ == "__main__":
    unittest.main()
