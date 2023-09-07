#!/usr/bin/python

import config
import paramiko
from rich.console import Console
from rich.panel import Panel

from history import ResultHistory, num_tokens_from_string
from targets.ssh import get_ssh_connection, SSHHostConn
from prompt_helper import LLM
from llms.manager import get_llm_connection
from dotenv import load_dotenv

# setup dotenv
load_dotenv()


# setup some infrastructure
cmd_history = ResultHistory()
console = Console()

# open SSH connection to target
conn = get_ssh_connection(config.target_ip(), config.target_user(), config.target_password())
conn.connect()

# initialize LLM connection
llm = LLM(get_llm_connection(config.llm_connection()))

context_size = config.context_size()
print("used model: " + config.model() + " context-size: " + str(config.context_size()))

# prepare an initial state
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

    state_size = num_tokens_from_string(state)

    next_cmd, diff = llm.create_and_ask_prompt('query_next_command.txt', "next-cmd", user=config.target_user(), password=config.target_password(), history=cmd_history.get_history(limit=context_size-state_size), state=state)

    if next_cmd["type"]  == "cmd":
        cmd, result = handle_cmd(next_cmd)
    elif next_cmd["type"] == "ssh":
        cmd, result = handle_ssh(next_cmd)

    # output the command and it's result
    console.print(Panel(result, title=cmd))

    # analyze the result and update your state
    resp_success, diff_2 = llm.create_and_ask_prompt('successfull.txt', 'success?', cmd=cmd, resp=result, facts=state)

    success = resp_success["success"]
    reason = resp_success["reason"]

    state = "\n".join(map(lambda x: "- " + x, resp_success["facts"]))
    console.print(Panel(state, title="my new fact list"))

    # update our command history and output it
    cmd_history.append(diff, next_cmd["type"], cmd, result, success, reason)
    console.print(cmd_history.create_history_table())