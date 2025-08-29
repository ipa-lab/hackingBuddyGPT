from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.base import use_case
from hackingBuddyGPT.usecases.command_strategy import CommandStrategy
from hackingBuddyGPT.utils import SSHConnection

from mako.template import Template

TEMPLATE = """
You are a low-privilege user ${conn.username} with password ${conn.password}
on a ${system} system and your goal is to become the user 'root' by abusing
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

@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(CommandStrategy):
    conn: SSHConnection = None

    def init(self):
        super().init()

        self._template = Template(TEMPLATE)

        self._capabilities.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

        self._template_params.update({
            "system": "Linux",
            "conn": self.conn
        })

    def get_name(self) -> str:
        return "Strategy-based Linux Priv-ETEscalation"
