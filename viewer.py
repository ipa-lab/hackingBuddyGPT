#!/usr/bin/python3

import argparse

from utils.db_storage import DbStorage
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# helper to fill the history table with data from the db
def get_history_table(run_id: int, db: DbStorage, round: int) -> Table:
    table = Table(title="Executed Command History", show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    #if config.enable_explanation:
    #    table.add_column("Explanation")
    #    table.add_column("ExplTime", style="dim")
    #    table.add_column("ExplTokens", style="dim")
    #if config.enable_update_state:
    #    table.add_column("StateUpdTime", style="dim")
    #    table.add_column("StateUpdTokens", style="dim")

    for i in range(0, round+1):
        table.add_row(*db.get_round_data(run_id, i, explanation=False, status_update=False))
        #, config.enable_explanation, config.enable_update_state))

    return table

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

# setup round meta-data
run_id : int = 1
round : int = 0

# read run data

run = db.get_run_data(run_id)
while run is not None:
    if run[4] is None:
        console.print(Panel(f"run: {run[0]}/{run[1]}\ntest: {run[2]}\nresult: {run[3]}", title="Run Data"))
    else:
        console.print(Panel(f"run: {run[0]}/{run[1]}\ntest: {run[2]}\nresult: {run[3]} after {run[4]} rounds", title="Run Data"))
    console.log(run[5])
    
    # Output Round Data
    console.print(get_history_table(run_id, db, run[4]-1))

    # fetch next run
    run_id += 1
    run = db.get_run_data(run_id)
