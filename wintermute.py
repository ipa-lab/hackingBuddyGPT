#!/usr/bin/python

import argparse
import os
from rich.console import Console
from rich.panel import Panel

from targets.ssh import get_ssh_connection
from llms.manager import get_llm_connection, get_potential_llm_connections
from dotenv import load_dotenv
from db_storage import DbStorage

from handlers import handle_cmd, handle_ssh
from helper import *
from llm_with_state import LLMWithState

# setup dotenv
load_dotenv()

# perform argument parsing
# for defaults we are using .env but allow overwrite through cli arguments
parser = argparse.ArgumentParser(description='Run an LLM vs a SSH connection.')
parser.add_argument('--log', type=str, help='sqlite3 db for storing log files', default=os.getenv("LOG_DESTINATION") or ':memory:')
parser.add_argument('--target-ip', nargs=1, help='ssh hostname to use to connect to target system', default=os.getenv("TARGET_IP") or '127.0.0.1')
parser.add_argument('--target-user', nargs=1, help='ssh username to use to connect to target system', default=os.getenv("TARGET_USER") or 'lowpriv')
parser.add_argument('--target-password', nargs=1, help='ssh password to use to connect to target system', default=os.getenv("TARGET_PASSWORD") or 'trustno1')
parser.add_argument('--max-rounds', type=int, help='how many cmd-rounds to execute at max', default=int(os.getenv("MAX_ROUNDS")) or 10)
parser.add_argument('--llm-connection', nargs=1, help='which LLM driver to use', choices=get_potential_llm_connections(), default=os.getenv("LLM_CONNECTION"))
parser.add_argument('--model', nargs=1, help='which LLM to use', default=os.getenv("MODEL") or "gpt-3.5-turbo")
parser.add_argument('--tag', type=str, help='tag run with string', default="")
parser.add_argument('--context-size', type=int, help='model context size to use', default=int(os.getenv("CONTEXT_SIZE")) or 3000)

args = parser.parse_args()

print("config-data: " + str(args))

# setup in-memory storage for command history
db = DbStorage(args.log)
print(f"using {args.log} for log storage")
db.connect()
db.setup_db()

# create an identifier for this session/run
run_id = db.create_new_run(args.model, args.context_size, args.tag)

# setup some infrastructure for outputing information
console = Console()

# open SSH connection to target
conn = get_ssh_connection(args.target_ip, args.target_user, args.target_password)
conn.connect()

# setup LLM connection and internal model representation
llm_connection = get_llm_connection(args.llm_connection, args.model, args.context_size)
console.log(llm_connection.output_metadata())
llm_gpt = LLMWithState(run_id, llm_connection, db, args.target_user, args.target_password)

# setup round meta-data
round : int = 0
gotRoot = False

# and start everything up
while round < args.max_rounds and not gotRoot:

    console.log(f"Starting round {round} of {args.max_rounds}")
    with console.status("[bold green]Asking LLM for a new command...") as status:
        answer = llm_gpt.get_next_cmd()

    with console.status("[bold green]Executing that command...") as status:
        if answer.result["type"]  == "cmd":
            cmd, result, gotRoot = handle_cmd(conn, answer.result)
        elif answer.result["type"] == "ssh":
            cmd, result = handle_ssh(args.target_ip, answer.result)

    db.add_log_query(run_id, round, cmd, result, answer)
 
    # output the command and its result
    console.print(Panel(result, title=cmd))

    # analyze the result..
    with console.status("[bold green]Analyze its result...") as status:
        answer = llm_gpt.analyze_result(cmd, result)
        db.add_log_analyze_response(run_id, round, cmd, answer.result["reason"], answer)

        # .. and let our local model representation update its state
        state = llm_gpt.update_state()
        db.add_log_update_state(run_id, round, "", state.result, None)
        
        # Output Round Data
        console.print(get_history_table(run_id, db, round))
        console.print(Panel(state.result, title="What does the LLM Know about the system?"))


    # finish round and commit logs to storage
    db.commit()
    round += 1

if gotRoot:
    db.run_was_success(run_id)
    console.print(Panel("Got Root!", title="Run finished"))
else:
    db.run_was_failure(run_id)
    console.print(Panel("maximum round number reached", title="Run finished"))