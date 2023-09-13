#!/usr/bin/python

import config
import os
import paramiko
from rich.console import Console
from rich.panel import Panel

from targets.ssh import get_ssh_connection, SSHHostConn
from prompt_helper import LLM
from llms.manager import get_llm_connection
from dotenv import load_dotenv
from db_storage import DbStorage

from helper import *

# setup dotenv
load_dotenv()

# setup in-memory storage
db = DbStorage()
db.connect()
db.setup_db()
run_id = db.create_new_run(os.getenv("MODEL"), os.getenv("CONTEXT_SIZE"))

# setup some infrastructure
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
    try:
        result, gotRoot = conn.run(input["cmd"])
    except Exception as e:
        result = "command timed out"
        gotRoot = False
    return input["cmd"], result, gotRoot

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

round : int = 0
max_rounds : int = config.max_rounds()

gotRoot = False
while round < max_rounds and not gotRoot:

    state_size = num_tokens_from_string(state)

    next_cmd, diff, tok_query, tok_res = llm.create_and_ask_prompt('query_next_command.txt', "next-cmd", user=config.target_user(), password=config.target_password(), history=get_cmd_history(run_id, db, context_size-state_size), state=state)

    if next_cmd["type"]  == "cmd":
        cmd, result, gotRoot = handle_cmd(next_cmd)
    elif next_cmd["type"] == "ssh":
        cmd, result = handle_ssh(next_cmd)

    db.add_log_query(run_id, round, cmd, result, diff, tok_query, tok_res)
 
    # output the command and it's result
    console.print(Panel(result, title=cmd))

    # analyze the result and update your state
    resp_success, diff_2, tok_query, tok_resp = llm.create_and_ask_prompt('successfull.txt', 'success?', cmd=cmd, resp=result, facts=state)

    db.add_log_analyze_response(run_id, round, cmd, resp_success["reason"], diff_2, tok_query, tok_resp)

    state = "\n".join(map(lambda x: "- " + x, resp_success["facts"]))
    console.print(Panel(state, title="my new fact list"))

    db.add_log_update_state(run_id, round, "", state, 0, 0, 0)

    # update our command history and output it
    console.print(get_history_table(run_id, db, round))
    round += 1
