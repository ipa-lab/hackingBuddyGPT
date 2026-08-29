from typing import override

from hackingBuddyGPT.capabilities import SSHRunCommand
from hackingBuddyGPT.capabilities.pentest_playbook import PentestPlaybook
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.usecase import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.web._base import WEB_PENTEST_TAIL, WebTestingAgent
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection
from hackingBuddyGPT.utils.limits import Limits


class WebTestingWithShell(WebTestingAgent):
    kali_conn: SSHConnection = None

    @override
    async def system_message(self, limits: Limits) -> str:
        message = self._system_message_head(flag_trailing_newline=False)

        if self.hints:
            message += f"Here are some hints to help you get started:\n{self.hints}\n"

        message += WEB_PENTEST_TAIL
        return message

    @override
    def _add_task_capabilities(self, limits: Limits, submit_flag_capability: SubmitFlag) -> None:
        self.add_capability(
            SSHRunCommand(
                conn=self.kali_conn,
                additional_description="You can use this capability to run commands on a kali linux machine that is in the same network as the server you want to attack.",
            )
        )
        self.add_capability(PentestPlaybook())


@use_case("Minimal implementation of a web testing use case with shell access")
class WebTestingWithShellUseCase(AutonomousAgentUseCase[WebTestingWithShell]):
    pass
