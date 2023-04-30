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

sysinfo = "This is a linux-based system."

while True:

    # TODO: separate between techniques (let GPT search for vulnerabiltiites) and procedures (concrete exploitation of a technique). This would make the exeuction loop a bit harder to understand and hierarchical, e.g., select a technique -> ask GPT how to exploit this technique (with a command sequence) -> execute and watch

    next_cmd = create_and_ask_prompt('query_next_command.txt', "next-cmd", user=initial_user, history=cmd_history.get_history())

    resp = conn.run(next_cmd)
    cmd_history.append(next_cmd, resp)

    # this will already by output by conn.run
    # logs.warning("server-output", resp)

    # aks chatgpt to explain what it expects about the tested
    # system. Understanding this might help human learning
    system_explanation = create_and_ask_prompt('explain_system.txt', 'explain-system', sysinfo=sysinfo, cmd=next_cmd, cmd_output=resp)

    # this asks for additional vulnerabilities identifiable in the last command output
    # create_and_ask_prompt('query_vulnerabilities.txt', 'vulns', user=initial_user, next_cmd=next_cmd, resp=resp)