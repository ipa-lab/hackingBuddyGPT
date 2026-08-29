"""Unit tests for the `AD` use-case (the cochise port): Knowledge, registration, and the
`perform_task` delegation capability (planner -> ephemeral worker -> knowledge merge)."""
import asyncio
import contextlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from hackingBuddyGPT.capabilities.ssh_execute_command import SSHExecuteCommand
from hackingBuddyGPT.usecases.ad.executor import PerformTaskCapability
from hackingBuddyGPT.usecases.ad.knowledge import Knowledge
from hackingBuddyGPT.utils.limits import Limits


# --------------------------------------------------------------------------------------------------
# helpers / fakes
# --------------------------------------------------------------------------------------------------
class FakeLogger:
    """Enough of the Logger surface for run_tool_calling_turn / ChatAgent / PerformTaskCapability."""

    def __init__(self):
        self.call_response = AsyncMock(return_value=1)
        self.add_tool_call = AsyncMock()
        self.status_message = AsyncMock()
        self.system_message = AsyncMock()
        self.limit_message = AsyncMock()

    @contextlib.asynccontextmanager
    async def section(self, name):
        yield


def tool_call(call_id, name, **arguments):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def assistant(tool_calls):
    return SimpleNamespace(tool_calls=tool_calls)


def llm_result(message, total_tokens=1, cost=0.0, answer=""):
    return SimpleNamespace(result=message, total_tokens=total_tokens, cost=cost, answer=answer)


def fake_conn(stdout="uid=0(root)"):
    conn = SimpleNamespace()
    conn.run = AsyncMock(return_value={"stdout": stdout, "output": stdout, "stderr": "", "exit_status": 0})
    conn.connect = AsyncMock()
    return conn


# --------------------------------------------------------------------------------------------------
# Knowledge
# --------------------------------------------------------------------------------------------------
class TestKnowledge(unittest.TestCase):
    def test_merge_copies_only_dirty_entries_and_clears_the_flag(self):
        local = Knowledge()
        asyncio.run(local.add_compromised_account("alice", "pw", "AS-REP roast"))
        asyncio.run(local.add_entity_information("dc01", "10.0.0.1, Domain Controller"))

        global_k = Knowledge()
        global_k.merge(local)

        self.assertEqual(len(global_k.compromised_accounts), 1)
        self.assertEqual(len(global_k.entity_information), 1)
        # dirty flag cleared after merge
        self.assertFalse(next(iter(global_k.compromised_accounts.values()))["dirty"])
        md = global_k.get_knowledge()
        self.assertIn("alice", md)
        self.assertIn("dc01", md)

        # a second merge with nothing newly dirty is a no-op
        global_k.merge(local)  # local entries are still dirty=True in local, so they re-copy...
        # ... but the important invariant is that already-merged, now-clean local entries don't duplicate:
        clean = Knowledge()
        clean.merge(global_k)  # global_k's entries are dirty=False -> nothing copied
        self.assertEqual(len(clean.compromised_accounts), 0)
        self.assertEqual(len(clean.entity_information), 0)

    def test_update_resolves_non_numeric_key_by_identity(self):
        k = Knowledge()
        asyncio.run(k.add_compromised_account("bob", "old", "spray"))
        # LLM passes the username instead of the numeric id -> resolved by identity, not a new row
        asyncio.run(k.update_compromised_account("bob", "bob", "new", "cracked"))
        self.assertEqual(len(k.compromised_accounts), 1)
        self.assertEqual(next(iter(k.compromised_accounts.values()))["password"], "new")


# --------------------------------------------------------------------------------------------------
# registration
# --------------------------------------------------------------------------------------------------
class TestRegistration(unittest.TestCase):
    def test_ad_use_case_is_registered(self):
        import hackingBuddyGPT.usecases  # noqa: F401  (import side effect registers use-cases)
        from hackingBuddyGPT.usecases.usecase import use_cases

        self.assertIn("AD", use_cases)


# --------------------------------------------------------------------------------------------------
# perform_task delegation
# --------------------------------------------------------------------------------------------------
class TestPerformTask(unittest.TestCase):
    def _capability(self, llm, log, conn, knowledge, max_rounds=25):
        return PerformTaskCapability(
            llm=llm,
            log=log,
            parent_limits=self._limits,
            ssh_capability=SSHExecuteCommand(conn=conn),
            knowledge=knowledge,
            scenario="SCENARIO",
            max_rounds=max_rounds,
        )

    def setUp(self):
        self._limits = Limits(max_rounds=0, max_tokens=0, max_cost=0, max_duration=0)
        self._limits.start()

    def test_worker_runs_ssh_merges_knowledge_and_returns_summary(self):
        log = FakeLogger()
        conn = fake_conn(stdout="uid=0(root)")
        global_k = Knowledge()

        # round 1: worker runs a command AND records a compromised account
        r1 = assistant([
            tool_call("c1", "execute_command", command="id", mitre_attack_technique="T1078",
                      mitre_attack_procedure="whoami"),
            tool_call("c2", "add_compromised_account", username="svc_sql", password="Summer2022!",
                      context="kerberoasted"),
        ])
        # round 2: worker finishes with a summary
        r2 = assistant([tool_call("c3", "complete", summary_text="Kerberoasted svc_sql and cracked it.")])

        llm = SimpleNamespace()
        llm.get_response = MagicMock(side_effect=[llm_result(r1), llm_result(r2)])

        cap = self._capability(llm, log, conn, global_k)
        out = asyncio.run(cap("Kerberoast the domain", "dc=10.0.0.1", "Credential Access", "T1558.003"))

        # SSH command executed
        conn.run.assert_awaited_with("id")
        # summary text + rendered local-knowledge markdown returned to the planner
        self.assertIn("Kerberoasted svc_sql", out)
        self.assertIn("svc_sql", out)
        # the worker's dirty knowledge merged into the planner's global knowledge
        self.assertEqual(len(global_k.compromised_accounts), 1)
        self.assertIn("svc_sql", global_k.get_knowledge())
        # exactly two model turns were consumed
        self.assertEqual(llm.get_response.call_count, 2)

    def test_forced_summary_when_worker_never_calls_complete(self):
        log = FakeLogger()
        conn = fake_conn()
        global_k = Knowledge()

        # one round, no complete -> worker exhausts its single round, summary is forced
        r1 = assistant([tool_call("c1", "execute_command", command="nxc smb 10.0.0.1",
                                  mitre_attack_technique="T1046", mitre_attack_procedure="scan")])
        forced = llm_result(SimpleNamespace(tool_calls=None), answer="Nothing worked; no creds found.")

        llm = SimpleNamespace()
        llm.get_response = MagicMock(side_effect=[llm_result(r1), forced])

        cap = self._capability(llm, log, conn, global_k, max_rounds=1)
        out = asyncio.run(cap("Enumerate SMB", "dc=10.0.0.1", "Discovery", "T1046"))

        self.assertIn("Nothing worked", out)
        # two calls: the single worker round + the forced-summary call
        self.assertEqual(llm.get_response.call_count, 2)


if __name__ == "__main__":
    unittest.main()
