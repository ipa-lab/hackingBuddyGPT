#!/usr/bin/python

import os
import time

from dotenv import load_dotenv

from history import ResultHistory, num_tokens_from_string
from targets.ssh import get_ssh_connection, SSHHostConn
from llms.openai_rest import openai_config, get_openai_response
from prompt_helper import create_and_ask_prompt

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

from mako.template import Template

# setup some infrastructure
cmd_history = ResultHistory()

# read configuration from env and configure system parts
load_dotenv()
openai_config()
conn = get_ssh_connection()
conn.connect()

print("Get initial user from virtual machine:")
initial_user = conn.run("whoami")

sysinfo = "This is a linux-based system."

console = Console()
table = Table(show_header=True, show_lines=True)
table.add_column("Type", style="dim", width=7)
table.add_column("ThnkTime", style="dim")
table.add_column("To_Execute")
table.add_column("Resp. Size", justify="right")
table.add_column("success?", width=8)
table.add_column("reason")

context_size = int(os.getenv("CONTEXT_SIZE"))
print("used model: " + os.getenv("MODEL") + " context-size: " + os.getenv("CONTEXT_SIZE"))

state = """
- this is a linux system
- your low privilege user credentials are lowpriv:trustno1
"""

# maybe generate list of potential vulnerabilities based upon the system facts


while True:
    # todo: take the list of potential vulnerabilities, go through each element and try up to 10 times to exploit the vulnerability

    state_size = num_tokens_from_string(state)

    tic = time.perf_counter()
    next_cmd = create_and_ask_prompt('query_next_command.txt', "next-cmd", user=initial_user, password=os.getenv("TARGET_PASSWORD"), history=cmd_history.get_history(limit=context_size-state_size), state=state)
    toc = time.perf_counter()
    diff = str(toc-tic)

    if next_cmd["type"]  == "cmd":
        cmd = next_cmd["cmd"]

        resp = conn.run(cmd)
        cmd_history.append(cmd, resp)

        console.print(Panel(resp, title=cmd))

        resp_success = create_and_ask_prompt('successfull.txt', 'success?', cmd=cmd, resp=resp, facts=state)
        table.add_row("cmd", diff, cmd, str(len(resp)), resp_success["success"], resp_success["reason"])

        state = "\n".join(map(lambda x: "- " + x, resp_success["facts"]))
        console.print(Panel(state, title="my new fact list"))

        # this asks for additional vulnerabilities identifiable in the last command output
        # next_vulns = create_and_ask_prompt('query_vulnerabilitites.txt', 'vulns', user=initial_user, next_cmd=cmd, resp=resp)
        # console.print(Panel(str(next_vulns), title="Next Vulns"))


    elif next_cmd["type"] == "ssh":
        ip = os.getenv('TARGET_IP')
        user = next_cmd["username"]
        password = next_cmd["password"]
        
        test = SSHHostConn(ip, user, password)
        print(str(test.test()))
        if result == "root":
            table.add_row("ssh", diff, next_cmd["username"] + ":" + next_cmd["password"], "0", "true", "you were able to login as user root")
        else:
            table.add_row("ssh", diff, next_cmd["username"] + ":" + next_cmd["password"], "0", "false", "result was: " + result)
            cmd_history.append("you tried to login through SSH with " + next_cmd["username"] + " and password + " + next_cmd["password"], "this was possible but the resulting account was not root")


    # this will already by output by conn.run
    # logs.warning("server-output", resp)

    # aks chatgpt to explain what it expects about the tested
    # system. Understanding this might help human learning
    # system_explanation = create_and_ask_prompt('explain_system.txt', 'explain-system', sysinfo=sysinfo, cmd=next_cmd, cmd_output=resp)


    console.print(table)
