#!/usr/bin/python3

import argparse
import os
import matplotlib.pyplot as plt

from db_storage import DbStorage
from rich.console import Console
from rich.panel import Panel

# setup infrastructure for outputing information
console = Console()

parser = argparse.ArgumentParser(description='Generate Graph for Context Size Usage.')
parser.add_argument('log', type=str, help='sqlite3 db for reading log data')
args = parser.parse_args()

# setup in-memory/persistent storage for command history
db = DbStorage(args.log)
db.connect()
db.setup_db()

# setup round meta-data
run_id : int = 1
round : int = 0

names = {
    "1" : "suid-gtfo",
    "2" : "sudo-all",
    "3" : "sudo-gtfo",
    "4" : "docker",
    "5" : "cron-script",
    "6" : "pw-reuse",
    "7" : "pw-root",
    "8" : "vacation",
    "9" : "ps-bash-hist",
    "10" : "cron-wildcard",
    "11" : "ssh-key",
    "12" : "cron-script-vis",
    "13" : "cron-wildcard-vis"
}

run = db.get_run_data(run_id)
while run != None:
    max_round = db.get_max_round_for(run_id)
    if run[4] == None:
        console.print(Panel(f"run: {run[0]}/{run[1]}\ntest: {run[2]}\nresult: {run[3]}", title="Run Data"))
    else:
        max_round = run[4]-1
        console.print(Panel(f"run: {run[0]}/{run[1]}\ntest: {run[2]}\nresult: {run[3]} after {run[4]} rounds", title="Run Data"))
    console.log(run[5])
    
    round_tokens = []
    for i in range(0, max_round+1):
        data = db.get_round_data(run_id, i, explanation=False, status_update=False)
        tokens = data[1].split("/")
        round_tokens.append(int(tokens[0]))

    plt.plot(round_tokens, label=names[str(run_id)])

    # fetch next run
    run_id += 1
    run = db.get_run_data(run_id)

plt.xlabel("Round Number")
plt.ylabel("Context Size in Tokens")
plt.legend()

ax = plt.gca()
ax.set_ylim([-650, 16599])
plt.savefig('tokens.png')
