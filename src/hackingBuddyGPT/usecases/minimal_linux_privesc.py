import re
from typing import List
from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.strategies import CommandStrategy
from hackingBuddyGPT.utils import llm_util
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection

from mako.template import Template

from hackingBuddyGPT.utils.shell_root_detection import got_root

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
    conn: SSHConnection = None

    def init(self):
        super().init()

        self._template = Template(TEMPLATE)

        self._capabilities.add_capability(SSHRunCommand(conn=self.conn), default=True)
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
        if cmd.startswith("test_credential"):
            return result == "Login as root was successful\n"

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        last_line = result.split("\n")[-1] if result else ""
        last_line = ansi_escape.sub("", last_line)
        return got_root(self.conn.hostname, last_line)