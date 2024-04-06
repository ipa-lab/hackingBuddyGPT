#!/usr/bin/python3

import argparse

from utils.db_storage import DbStorage
from rich.console import Console
from rich.table import Table

# setup infrastructure for outputing information
console = Console()

parser = argparse.ArgumentParser(description='View an existing log file.')
parser.add_argument('log', type=str, help='sqlite3 db for reading log data')
args = parser.parse_args()
console.log(args)

# setup in-memory/persistent storage for command history
db = DbStorage(args.log)
db.connect()
db.setup_db()

# experiment names
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

# prepare table
table = Table(title="Round Data", show_header=True, show_lines=True)
table.add_column("RunId", style="dim")
table.add_column("Description", style="dim")
table.add_column("Round", style="dim")
table.add_column("State")
table.add_column("Last Command")

data = db.get_log_overview()
for run in data:
    row = data[run]
    table.add_row(str(run), names[str(run)], str(row["max_round"]), row["state"], row["last_cmd"])

console.print(table)
