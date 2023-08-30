#!/usr/bin/python

import config
import time
import paramiko
from rich.console import Console
from rich.panel import Panel

from history import ResultHistory, num_tokens_from_string
from targets.ssh import get_ssh_connection, SSHHostConn
from llms.openai_rest import get_openai_response
from prompt_helper import LLM

# setup some infrastructure
cmd_history = ResultHistory()
console = Console()

# read configuration from env and configure system parts
config.check_config()

# open SSH connection to target
conn = get_ssh_connection(config.target_ip(), config.target_user(), config.target_password())
conn.connect()

# TODO: why do I even have this code?
print("Get initial user from virtual machine:")
initial_user = conn.run("whoami")

# initialize LLM connection
llm = LLM(get_openai_response)

context_size = config.context_size()
print("used model: " + config.model() + " context-size: " + str(config.context_size()))

# prepare an initial state
sysinfo = "This is a linux-based system."

state = """
- this is a linux system
- your low privilege user credentials are lowpriv:trustno1
"""

def handle_cmd(input):
    return input["cmd"], conn.run(input["cmd"])

def handle_ssh(input):
    user = input["username"]
    password = input["password"]

    cmd = "tried ssh with username " + user + " and password " + password

    test = SSHHostConn(config.target_ip(), user, password)
    try:
        test.connect()
        user = conn.run("whoami")

        if user == "root":
            return cmd, "Login as root was successful"
        else:
            return cmd, "Authentication successful, but user is not root"

    except paramiko.ssh_exception.AuthenticationException:
        return cmd, "Authentication error, credentials are wrong"

while True:
    # todo: take the list of potential vulnerabilities, go through each element and try up to 10 times to exploit the vulnerability

    state_size = num_tokens_from_string(state)

    tic = time.perf_counter()
    next_cmd = llm.create_and_ask_prompt('query_next_command.txt', "next-cmd", user=initial_user, password=config.target_password(), history=cmd_history.get_history(limit=context_size-state_size), state=state)
    toc = time.perf_counter()
    diff = str(toc-tic)

    if next_cmd["type"]  == "cmd":
        cmd, result = handle_cmd(next_cmd)

        # this asks for additional vulnerabilities identifiable in the last command output
        # next_vulns = create_and_ask_prompt('query_vulnerabilitites.txt', 'vulns', user=initial_user, next_cmd=cmd, resp=resp)
        # console.print(Panel(str(next_vulns), title="Next Vulns"))

    elif next_cmd["type"] == "ssh":
        cmd, result = handle_ssh(next_cmd)

    # output the command and it's result
    console.print(Panel(result, title=cmd))

    # analyze the result and update your state
    resp_success = llm.create_and_ask_prompt('successfull.txt', 'success?', cmd=cmd, resp=result, facts=state)

    success = resp_success["success"]
    reason = resp_success["reason"]

    state = "\n".join(map(lambda x: "- " + x, resp_success["facts"]))
    console.print(Panel(state, title="my new fact list"))

    # update our command history and output it
    cmd_history.append(diff, next_cmd["type"], cmd, result, success, reason)
    console.print(cmd_history.create_history_table())

    # aks chatgpt to explain what it expects about the tested
    # system. Understanding this might help human learning
    # system_explanation = create_and_ask_prompt('explain_system.txt', 'explain-system', sysinfo=sysinfo, cmd=next_cmd, cmd_output=resp)