from typing import override

from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.capabilities.pentest_playbook import PentestPlaybook
from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.usecase import AutonomousAgentUseCase, use_case
from hackingBuddyGPT.usecases.web._base import WEB_PENTEST_TAIL, WebTestingAgent
from hackingBuddyGPT.utils.limits import Limits


class WebTestingWithExplanation(WebTestingAgent):
    @override
    async def system_message(self, limits: Limits) -> str:
        message = self._system_message_head(flag_trailing_newline=True)

        if self.hints:
            message += f"Here are some hints to help you get started:\n{self.hints}\n"

        message += WEB_PENTEST_TAIL
        return message

    @override
    def _add_task_capabilities(self, limits: Limits, submit_flag_capability: SubmitFlag) -> None:
        self.add_capability(HTTPRequest(self.host))
        self.add_capability(PentestPlaybook())


@use_case("Minimal implementation of a web testing use case while allowing the llm to 'talk'")
class WebTestingWithExplanationUseCase(AutonomousAgentUseCase[WebTestingWithExplanation]):
    pass
