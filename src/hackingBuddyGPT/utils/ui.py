from rich.table import Table

from .db_storage.db_storage import DbStorage


# helper to fill the history table with data from the db
def get_history_table(
    enable_explanation: bool, enable_update_state: bool, run_id: int, db: DbStorage, turn: int
) -> Table:
    table = Table(title="Executed Command History", show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    if enable_explanation:
        table.add_column("Explanation")
        table.add_column("ExplTime", style="dim")
        table.add_column("ExplTokens", style="dim")
    if enable_update_state:
        table.add_column("StateUpdTime", style="dim")
        table.add_column("StateUpdTokens", style="dim")

    for i in range(1, turn + 1):
        table.add_row(*db.get_round_data(run_id, i, enable_explanation, enable_update_state))

    return table
