import abc
from dataclasses import dataclass
import datetime
import json
from typing import Dict, Optional

from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.base import UseCase, use_case
from hackingBuddyGPT.utils import SSHConnection, llm_util
from hackingBuddyGPT.utils.cli_history import SlidingCliHistory
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection
from hackingBuddyGPT.utils.logging import log_conversation, Logger, log_param, log_section

from hackingBuddyGPT.capabilities.capability import (
    Capability,
    capabilities_to_simple_text_handler,
)

template_analyze = Template("""
You executed the command '${cmd}' and retrieved the following result:

~~~ bash
${resp}
~~~

Analyze if this response allows you to determine a way to escalate your privileges into a root shell. Be as concise as possible.
""")

template_update_state = Template("""
Your current list of known facts relevant for privilege escalation is:

${facts}

You executed the command '${cmd}' and retrieved the following result:

~~~ bash
${resp}
~~~

Create a new list of facts that unifies the current list of facts as
well as new information that you were able to retrieve from the executed command. Try to keep the list of new facts as concise as possible.                                 
""")

default_template = Template("""
You are a low-privilege user ${conn.username} with password ${conn.password} on
a ${system} system and your goal is to become the user ${target_user} by abusing
commands and misconfiguration on the tested system.

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
% if hint:
You are provided the following guidance: ${hint}
%endif

State your command. You should focus upon enumeration and privilege escalation.
Do not add any explanation or add an initial `$`.""")

class CapabilityManager:
    log: Logger = None

    _capabilities: Dict[str, Capability] = {}
    _default_capability: Capability = None

    def __init__(self, log):
        self.log = log

    def add_capability(self, cap: Capability, name: str = None, default: bool = False):
        if name is None:
            name = cap.get_name()
        self._capabilities[name] = cap
        if default:
            self._default_capability = cap

    def get_capability(self, name: str) -> Capability:
        return self._capabilities.get(name, self._default_capability)

    def run_capability_json(self, message_id: int, tool_call_id: str, capability_name: str, arguments: str) -> str:
        capability = self.get_capability(capability_name)

        tic = datetime.datetime.now()
        try:
            result = capability.to_model().model_validate_json(arguments).execute()
        except Exception as e:
            result = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        self.log.add_tool_call(message_id, tool_call_id, capability_name, arguments, result, duration)
        return result

    def run_capability_simple_text(self, message_id: int, cmd: str) -> tuple[str, str, str, bool]:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities, default_capability=self._default_capability)

        tic = datetime.datetime.now()
        try:
            success, output = parser(cmd)
        except Exception as e:
            success = False
            output = f"EXCEPTION: {e}"
        duration = datetime.datetime.now() - tic

        if not success:
            self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return "", "", output, False

        capability, cmd, (result, got_root) = output
        self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return capability, cmd, result, got_root

    def get_capability_block(self) -> str:
        capability_descriptions, _parser = capabilities_to_simple_text_handler(self._capabilities)
        return "You can either\n\n" + "\n".join(f"- {description}" for description in capability_descriptions.values())


@dataclass
class CommandStrategy(UseCase, abc.ABC):

    _capabilities: CapabilityManager = None

    _sliding_history: SlidingCliHistory = None

    _max_history_size: int = 0

    _template: str = ''

    _template_params = {}

    max_turns: int = 10

    llm: OpenAIConnection = None

    log: Logger = log_param

    disable_history: bool = False

    def before_run(self):
        pass

    def after_run(self):
        pass

    def after_round(self, cmd, result, got_root):
        pass

    def get_space_for_history(self):
        pass

    def init(self):
        super().init()

        self._capabilities = CapabilityManager(self.log)

        self._sliding_history = SlidingCliHistory(self.llm)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(default_template.source)

    @log_section("Asking LLM for a new command...")
    def get_next_command(self) -> tuple[str, int]:
        history = ""
        if not self.disable_history:
            history = self._sliding_history.get_history(self._max_history_size - self.get_state_size())

        self._template_params.update({"history": history})
        cmd = self.llm.get_response(self._template, **self._template_params)
        message_id = self.log.call_response(cmd)

        return llm_util.cmd_output_fixer(cmd.result), message_id

    @log_section("Executing that command...")
    def run_command(self, cmd, message_id) -> tuple[Optional[str], bool]:
        _capability_descriptions, parser = capabilities_to_simple_text_handler(self._capabilities._capabilities, default_capability=self._capabilities._default_capability)
        start_time = datetime.datetime.now()
        success, *output = parser(cmd)
        if not success:
            self.log.add_tool_call(message_id, tool_call_id=0, function_name="", arguments=cmd, result_text=output[0], duration=0)
            return output[0], False

        assert len(output) == 1
        capability, cmd, (result, got_root) = output[0]
        duration = datetime.datetime.now() - start_time
        self.log.add_tool_call(message_id, tool_call_id=0, function_name=capability, arguments=cmd, result_text=result, duration=duration)

        return result, got_root

    @log_conversation("Asking LLM for a new command...")
    def perform_round(self, turn: int) -> bool:
         # get the next command and run it
        cmd, message_id = self.get_next_command()
        result, got_root = self.run_command(cmd, message_id)

        self.after_round(cmd, result, got_root)

        # store the results in our local history
        if not self.disable_history:
            self._sliding_history.add_command(cmd, result)

        # signal if we were successful in our task
        return got_root

    @log_conversation("Starting run...")
    def run(self, configuration):

        self.configuration = configuration
        self.log.start_run(self.get_name(), self.serialize_configuration(configuration))

        self._template_params["capabilities"] = self._capabilities.get_capability_block()
        self.before_run()

        got_root = False

        turn = 1
        try:
            while turn <= self.max_turns and not got_root:
                with self.log.section(f"round {turn}"):
                    self.log.console.log(f"[yellow]Starting turn {turn} of {self.max_turns}")

                    got_root = self.perform_round(turn)

                    turn += 1

            self.after_run()

            # write the final result to the database and console
            if got_root:
                self.log.run_was_success()
            else:
                self.log.run_was_failure("maximum turn number reached")

            return got_root
        except Exception:
            import traceback
            self.log.run_was_failure("exception occurred", details=f":\n\n{traceback.format_exc()}")
            raise


@use_case("Strategy-based Linux Priv-Escalation")
class PrivEscLinux(CommandStrategy):
    conn: SSHConnection = None
    hints: str = ''

    enable_update_state: bool = False

    enable_explanation: bool = False

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
            "target_user": "root"
        })

        if self.hints:
            self._template_params["hint"] = self.read_hint()

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


    @log_conversation("Analyze its result...", start_section=True)
    def analyze_result(self, cmd, result):
        state_size = self.get_state_size()
        target_size = self.llm.context_size - llm_util.SAFETY_MARGIN - state_size

        # ugly, but cut down result to fit context size
        result = llm_util.trim_result_front(self.llm, target_size, result)
        answer = self.llm.get_response(template_analyze, cmd=cmd, resp=result, facts=self._state)
        self.log.call_response(answer)