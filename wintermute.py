#!/usr/bin/python

from dotenv import load_dotenv

from history import ResultHistory
from targets.ssh import get_ssh_connection
from llms.openai import openai_config
from prompt_helper import create_and_ask_prompt

# setup some infrastructure
cmd_history = ResultHistory()

# read configuration from env and configure system parts
load_dotenv()
openai_config()
conn = get_ssh_connection()
conn.connect()

print("Get initial user from virtual machine:")
initial_user = conn.run("whoami")

while True:

    next_cmd = create_and_ask_prompt('gpt_query.txt', "next-cmd", user=initial_user, history=cmd_history.get_history())

    # disable this for now, it's tragic because the AI won't tell me why it had chosen something
    # create_and_ask_prompt("why.txt", "why", user=initial_user, history=cmd_history.dump(), next_cmd=next_cmd)

    resp = conn.run(next_cmd)
    cmd_history.append(next_cmd, resp)

    # this will already by output by conn.run
    # logs.warning("server-output", resp)

    # this asks for additional vulnerabilities identifiable in the last command output
    # create_and_ask_prompt('further_information.txt', 'vulns', user=initial_user, next_cmd=next_cmd, resp=resp)