"""Unit tests for PSExecTestCredential's identity-aware credential check.

A fake PSExec connection maps `whoami` probes to canned output so the capability can be exercised
without a real Windows target. Verifies that a valid *admin* login reports root success, a valid
*non-admin* login reports success-but-not-admin, and a failed login reports an auth error.
"""
import asyncio

from hackingBuddyGPT.capabilities.psexec_test_credential import PSExecTestCredential
from hackingBuddyGPT.utils.shell_root_detection import LOGIN_AS_ROOT_SUCCESSFUL


class FakePSExec:
    def __init__(self, *, login_ok=True, groups="", who=""):
        self._login_ok = login_ok
        self._groups = groups
        self._who = who

    def new_with(self, *, username, password):
        return self

    def init(self):
        if not self._login_ok:
            raise RuntimeError("authentication failed")

    def run(self, cmd):
        out = self._groups if "groups" in cmd else self._who
        return (out, "", 0)


def _call(conn, username="admin", password="pw"):
    return asyncio.run(PSExecTestCredential(conn=conn)(username, password))


def test_admin_login_reports_root_success():
    conn = FakePSExec(groups="BUILTIN\\Administrators S-1-5-32-544 Enabled group", who="WINBOX\\admin")
    assert _call(conn) == LOGIN_AS_ROOT_SUCCESSFUL


def test_system_login_reports_root_success():
    # the SYSTEM account is a member of Administrators, so its /groups output carries the SID too
    conn = FakePSExec(groups="NT AUTHORITY\\SYSTEM S-1-5-18\nBUILTIN\\Administrators S-1-5-32-544 Enabled group")
    assert _call(conn) == LOGIN_AS_ROOT_SUCCESSFUL


def test_non_admin_login_reports_not_administrator():
    conn = FakePSExec(groups="Everyone S-1-1-0 Mandatory group", who="WINBOX\\bob")
    assert _call(conn, "bob", "pw") == "Authentication successful, but user WINBOX\\bob is not an administrator\n"


def test_filtered_admin_token_deny_only_is_not_admin():
    # a non-elevated admin: Administrators present but "for deny only" -> not elevated
    conn = FakePSExec(
        groups="BUILTIN\\Administrators S-1-5-32-544 Group used for deny only",
        who="WINBOX\\alice",
    )
    assert _call(conn, "alice", "pw") == "Authentication successful, but user WINBOX\\alice is not an administrator\n"


def test_failed_login_reports_auth_error():
    conn = FakePSExec(login_ok=False)
    assert _call(conn, "bob", "wrong") == "Authentication error, credentials bob:wrong are wrong\n"
