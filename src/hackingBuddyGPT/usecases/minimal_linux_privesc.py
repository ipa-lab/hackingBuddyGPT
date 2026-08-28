from typing import List

from mako.template import Template

from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from hackingBuddyGPT.strategies import CommandStrategy
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection
from hackingBuddyGPT.utils.shell_root_detection import check_command_success

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

@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(CommandStrategy):
    conn: SSHInteractiveConnection = None

    def init(self):
        super().init()

        self._template = Template(TEMPLATE)

        self._capabilities.add_capability(SSHInteractiveRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

        self._template_params.update({
            "system": "Linux",
            "target_user": "root",
            "conn": self.conn
        })

    def postprocess_commands(self, cmd:str) -> List[str]:
        return [llm_util.cmd_output_fixer(cmd)]

    def get_name(self) -> str:
        return self.__class__.__name__

    def check_success(self, cmd:str, result:str) -> bool:
        return check_command_success(self.conn.hostname, cmd, result, uid=self.conn.last_uid)