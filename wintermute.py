#!/usr/bin/python

import config
import os
from rich.console import Console
from rich.panel import Panel

from targets.ssh import get_ssh_connection
from llms.manager import get_llm_connection
from dotenv import load_dotenv
from db_storage import DbStorage

from handlers import handle_cmd, handle_ssh
from helper import *
from llm_with_state import LLMWithState

# setup dotenv
load_dotenv()

# setup in-memory storage
db = DbStorage()
db.connect()
db.setup_db()

# create an identifier for this session/run
run_id = db.create_new_run(os.getenv("MODEL"), os.getenv("CONTEXT_SIZE"))

# setup some infrastructure
console = Console()

# open SSH connection to target
conn = get_ssh_connection(config.target_ip(), config.target_user(), config.target_password())
conn.connect()

# setup LLM connection and internal model representation
llm_connection = get_llm_connection(config.llm_connection())
console.log(llm_connection.output_metadata())
llm_gpt = LLMWithState(run_id, llm_connection, db, config.target_user(), config.target_password())

# setup round meta-data
round : int = 0
max_rounds : int = config.max_rounds()
gotRoot = False

# and start everything up
while round < max_rounds and not gotRoot:

    console.log(f"Starting round {round} of {max_rounds}")

    next_cmd, diff, tok_query, tok_res = llm_gpt.get_next_cmd()

    if next_cmd["type"]  == "cmd":
        cmd, result, gotRoot = handle_cmd(conn, next_cmd)
    elif next_cmd["type"] == "ssh":
        cmd, result = handle_ssh(next_cmd)

    db.add_log_query(run_id, round, cmd, result, diff, tok_query, tok_res)
 
    # output the command and it's result
    console.print(Panel(result, title=cmd))

    # analyze the result and update your state
    resp_success, diff_2, tok_query, tok_resp = llm_gpt.analyze_result(cmd, result)
    db.add_log_analyze_response(run_id, round, cmd, resp_success["reason"], diff_2, tok_query, tok_resp)

    state = llm_gpt.update_state()
    console.print(Panel(state, title="my new fact list"))
    db.add_log_update_state(run_id, round, "", state, 0, 0, 0)

    # update our command history and output it
    console.print(get_history_table(run_id, db, round))
    round += 1
