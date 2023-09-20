#!/usr/bin/python

import json
import argparse
import os
from rich.console import Console
from rich.panel import Panel

from targets.ssh import get_ssh_connection
from targets.psexec import get_smb_connection

from llms.llm_connection import get_llm_connection, get_potential_llm_connections
from dotenv import load_dotenv
from db_storage import DbStorage

from handlers import handle_cmd, handle_ssh
from helper import *
from llm_with_state import LLMWithState, get_empty_result

# setup dotenv
load_dotenv()

# perform argument parsing
# for defaults we are using .env but allow overwrite through cli arguments
parser = argparse.ArgumentParser(description='Run an LLM vs a SSH connection.')
parser.add_argument('--enable-explanation', help="let the LLM explain each round's result", action="store_true")
parser.add_argument('--enable-update-state', help='ask the LLM to keep a multi-round state with findings', action="store_true")
parser.add_argument('--log', type=str, help='sqlite3 db for storing log files', default=os.getenv("LOG_DESTINATION") or ':memory:')
parser.add_argument('--target-ip', type=str, help='ssh hostname to use to connect to target system', default=os.getenv("TARGET_IP") or '127.0.0.1')
parser.add_argument('--target-hostname', type=str, help='safety: what hostname to exepct at the target IP', default=os.getenv("TARGET_HOSTNAME") or "debian")
parser.add_argument('--target-user', type=str, help='ssh username to use to connect to target system', default=os.getenv("TARGET_USER") or 'lowpriv')
parser.add_argument('--target-password', type=str, help='ssh password to use to connect to target system', default=os.getenv("TARGET_PASSWORD") or 'trustno1')
parser.add_argument('--max-rounds', type=int, help='how many cmd-rounds to execute at max', default=int(os.getenv("MAX_ROUNDS")) or 10)
parser.add_argument('--llm-connection', type=str, help='which LLM driver to use', choices=get_potential_llm_connections(), default=os.getenv("LLM_CONNECTION") or "openai_rest")
parser.add_argument('--target-os', type=str, help='What is the target operating system?', choices=["linux", "windows"], default="linux")
parser.add_argument('--model', type=str, help='which LLM to use', default=os.getenv("MODEL") or "gpt-3.5-turbo")
parser.add_argument('--llm-server-base-url', type=str, help='which LLM server to use', default=os.getenv("LLM_SERVER_BASE_URL") or "https://api.openai.com")
parser.add_argument('--tag', type=str, help='tag run with string', default="")
parser.add_argument('--context-size', type=int, help='model context size to use', default=int(os.getenv("CONTEXT_SIZE")) or 4096)
parser.add_argument('--hints', type=argparse.FileType('r', encoding='latin-1'), help='json file with a hint per tested hostname', default=None)

args = parser.parse_args()

# setup some infrastructure for outputing information
console = Console()
console.log("[yellow]Configuration for this Run:")
console.log(args)

# setup in-memory storage for command history
db = DbStorage(args.log)
db.connect()
db.setup_db()

# create an identifier for this session/run
run_id = db.create_new_run(args)

if args.target_os == 'linux':
    # open SSH connection to target
    conn = get_ssh_connection(args.target_ip, args.target_hostname, args.target_user, args.target_password)
    conn.connect()
else:
    conn = get_smb_connection(args.target_ip, args.target_hostname, args.target_user, args.target_password)
    conn.connect()

# setup LLM connection and internal model representation
llm_connection = get_llm_connection(args)
console.log(llm_connection.output_metadata())

# setup round meta-data
round : int = 0
gotRoot = False

# those are (optional) hints for my ai priv-esc testbed
hint = None
if args.hints:
    try:
        hints = json.load(args.hints)
        if args.target_hostname in hints:
            hint = hints[args.target_hostname]
            console.print(f"[bold green]Using the following hint: '{hint}'")
    except:
        console.print("[yellow]Was not able to load hint file")

# some configuration options
enable_state_update = False

# instantiate the concrete LLM model
llm_gpt = LLMWithState(run_id, llm_connection, db, args.target_user, args.target_password, args.enable_update_state, args.target_os, hint = hint)

# and start everything up
while round < args.max_rounds and not gotRoot:

    console.log(f"[yellow]Starting round {round+1} of {args.max_rounds}")
    with console.status("[bold green]Asking LLM for a new command...") as status:
        answer = llm_gpt.get_next_cmd()

    with console.status("[bold green]Executing that command...") as status:
        if answer.result["type"]  == "cmd":
            console.print(Panel(answer.result["cmd"], title=f"[bold cyan]Got command from LLM:"))
            cmd, result, gotRoot = handle_cmd(conn, answer.result)
        elif answer.result["type"] == "ssh":
            cmd, result, gotRoot = handle_ssh(args.target_ip, args.target_hostname, answer.result)

    db.add_log_query(run_id, round, cmd, result, answer)
 
    # output the command and its result
    console.print(Panel(result, title=f"[bold cyan]{cmd}"))

    # analyze the result..
    if args.enable_explanation:
        with console.status("[bold green]Analyze its result...") as status:
            answer = llm_gpt.analyze_result(cmd, result)
            db.add_log_analyze_response(run_id, round, cmd.strip("\n\r"), answer.result.strip("\n\r"), answer)

    # .. and let our local model representation update its state
    if args.enable_update_state:
        # this must happen before the table output as we might include the
        # status processing time in the table..
        with console.status("[bold green]Updating fact list..") as status:
            state = llm_gpt.update_state(cmd, result)
            db.add_log_update_state(run_id, round, "", state.result, state)
    
    # Output Round Data
    console.print(get_history_table(args, run_id, db, round))

    if args.enable_update_state:
        console.print(Panel(llm_gpt.get_current_state(), title="What does the LLM Know about the system?"))

    # finish round and commit logs to storage
    db.commit()
    round += 1

if gotRoot:
    db.run_was_success(run_id, round)
    console.print(Panel("[bold green]Got Root!", title="Run finished"))
else:
    db.run_was_failure(run_id, round)
    console.print(Panel("[green]maximum round number reached", title="Run finished"))
