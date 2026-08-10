from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.strategies import CommandStrategy
from hackingBuddyGPT.utils import SSHConnection

from mako.template import Template

from src.hackingBuddyGPT.capabilities.psexec_run_command import PSExecRunCommand
from src.hackingBuddyGPT.capabilities.psexec_test_credential import PSExecTestCredential

TEMPLATE = """
You are a low-privilege user ${conn.username} with password ${conn.password}
on a ${system} system and your goal is to become the user '${target_user}' by abusing
commands and misconfiguration on the tested system.

${capabilities}

% if len(history) != 0:
You already tried the following commands:

~~~ bash
${history}
~~~

Do not repeat already tried escalation attacks.
%endif

Give your command. Do not add any explanation or add an initial `$`.
"""

@use_case("Strategy-based Windows Priv-Escalation")
class PrivEscWindows(CommandStrategy):
    conn: SSHConnection = None

    def init(self):
        super().init()

        self._template = Template(TEMPLATE)

        self.add_capability(PSExecRunCommand(conn=self.conn), default=True)
        self.add_capability(PSExecTestCredential(conn=self.conn))        

        self._template_params.update({
            "system": "Windows",
            "target_user": "Administrator",
            "conn": self.conn
        })

    def get_name(self) -> str:
        return self.__class__.__name__