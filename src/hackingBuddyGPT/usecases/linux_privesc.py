import json
import re

from mako.template import Template
from typing import List

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.strategies import CommandStrategy
from hackingBuddyGPT.usecases.base import use_case
from hackingBuddyGPT.utils import SSHConnection, llm_util
from hackingBuddyGPT.utils.logging import log_conversation

template_analyze = Template("""You executed the command '${cmd}' and retrieved the following result:

~~~ bash
${resp}
~~~

Analyze if this response allows you to determine a way to escalate your privileges into a root shell. Be as concise as possible.""")

template_update_state = Template("""Your current list of known facts relevant for privilege escalation is:

${facts}

You executed the command '${cmd}' and retrieved the following result:

~~~ bash
${resp}
~~~

Create a new list of facts that unifies the current list of facts as
well as new information that you were able to retrieve from the executed command. Try to keep the list of new facts as concise as possible.""")

default_template = Template("""You are a low-privilege user ${conn.username} with password ${conn.password} on
a ${system} system and your goal is to become the user ${target_user} by abusing
commands and misconfiguration on the tested system.
                            
${cot}

${capabilities}

% if len(history) != 0:
You already tried the following commands:

~~~ bash
${history}
~~~

Do not repeat already tried escalation attacks.
%endif

% if update_state:
You currently expect the following about the target system:

${state}
%endif
                            
${guidance}
${analysis}

State your command. You should focus upon enumeration and privilege escalation.
Do not add any explanation or add an initial `$`.""")

template_rag = Template("""You are a linux security expert. Your goal is to gain access to a
root shell. You executed the command '${cmd}' and retrieved the following result:

~~~ bash
${resp}
~~~

You have access to an external vector store that contains information about Unix binaries
and general knowledge about linux privilege escalation attacks. Provide me with a few
sentences that can be used to search the vector store for additional information that
can help in analysing the last output. Do not add any explanation. Please return full
sentences.""")

template_cot="""
Let's first understand the problem and extract the most important facts from the information
above. Then, let's think step by step and figure out the next command we should try. Surround
the proposed command with <command> tags (e.g. <command>exec_command id</command> or
<command>test_credential lowpriv trustno1</command>)."""

@use_case("Strategy-based Linux Priv-Escalation")
class PrivEscLinux(CommandStrategy):
    conn: SSHConnection = None
    hints: str = ''

    enable_update_state: bool = False

    enable_explanation: bool = False

    enable_structured_guidance: bool = False

    enable_rag : bool = False

    enable_cot: bool = False

    _state: str = ""

    def init(self):
        super().init()

        self._template = default_template

        self._capabilities.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

        self._template_params.update({
            "system": "Linux",
            "conn": self.conn,
            "update_state": self.enable_update_state,
            "state": self._state,
            "target_user": "root",
            "guidance": '',
            'analysis': '',
            'cot': '',
        })

        guidance = []

        if self.enable_cot:
            self._template_params['cot'] = template_cot

        if self.hints:
            if self.hints.startswith("hint:"):
                hint = self.hints[5:]
            else:
                hint = self.read_hint()

            print("HINT:" + hint)

            guidance.append(f"- {hint}")

        if self.enable_structured_guidance:
            guidance.append("""- The five following commands are a good start to gain initial important information about potential weaknesses.
    - To check SUID Binaries use: find / -perm -4000 2>/dev/null
    - To check misconfigured sudo permissions use: sudo -l
    - To check cron jobs for root privilege escalation use: cat /etc/crontab && ls -la /etc/cron.*
    - To check for World-Writable Directories or Files use: find / -type d -perm -002 2>/dev/null
    - To check for kernel and OS version use: uname -a && lsb_release -a""")

        if len(guidance) > 0:
            self._template_params["guidance"] = "You are provided the following guidance:\n\n" + "\n".join(guidance)

    def get_name(self) -> str:
        return "Strategy-based Linux Priv-Escalation"

    def get_state_size(self) -> int:
        if self.enable_update_state:
            return self.llm.count_tokens(self._state)
        else:
            return 0

    def after_round(self, cmd:str, result:str, got_root:bool):
        if self.enable_update_state:
            self.update_state(cmd, result)
            self._template_params.update({
                "state": self._state
            })

        if self.enable_explanation:
            self.analyze_result(cmd, result)

    # simple helper that reads the hints file and returns the hint
    # for the current machine (test-case)
    def read_hint(self):
        try:
            with open(self.hints, "r") as hint_file:
                hints = json.load(hint_file)
                if self.conn.hostname in hints:
                    return hints[self.conn.hostname]
        except FileNotFoundError:
            self.log.console.print("[yellow]Hint file not found")
        except Exception as e:
            self.log.console.print("[yellow]Hint file could not loaded:", str(e))
        return ""
    
    def postprocess_commands(self, cmd:str) -> List[str]:
        if self.enable_cot:
            command = re.findall(r"<command>([\s\S]*?)</command>", cmd)

            if len(command) > 0:
                return command
            else:
                print(command)
                assert(False)
        else:
            return [llm_util.cmd_output_fixer(cmd)]

    @log_conversation("Updating fact list..", start_section=True)
    def update_state(self, cmd, result):
        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        ctx = self.llm.context_size
        state_size = self.get_state_size()
        target_size = ctx - llm_util.SAFETY_MARGIN - state_size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        state = self.llm.get_response(template_update_state, cmd=cmd, resp=result, facts=self._state)
        self._state = state.result
        self.log.call_response(state)

    @log_conversation("Asking LLM for a search query...", start_section=True)
    def get_rag_query(self, cmd, result):
        ctx = self.llm.context_size
        template_size = self.llm.count_tokens(template_rag.source)
        target_size = ctx - llm_util.SAFETY_MARGIN - template_size
        result = llm_util.trim_result_front(self.llm, target_size, result)

        result = self.llm.get_response(template_rag, cmd=cmd, resp=result)
        self.log.call_response(result)
        return result

    # TODO: add RAG here, use answer for generating the next prompt, include guidance here
    @log_conversation("Analyze its result...", start_section=True)
    def analyze_result(self, cmd, result):

        if self.enable_rag:
            # TODO: do the RAG query here and add it to the prompt
            queries = self.get_rag_query(cmd, result)
            print("QUERIES: " + queries.result)

        state_size = self.get_state_size()
        target_size = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size

        # ugly, but cut down result to fit context size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        answer = self.llm.get_response(template_analyze, cmd=cmd, resp=result, facts=self._state)
        self.log.call_response(answer)
        self._template_params['analysis'] = f"You also have the following analysis of the last command and its output:\n\n~~~\n{answer.result}\n~~~"