from rich.table import Table

from .db_storage.db_storage import DbStorage

# helper to fill the history table with data from the db
def get_history_table(enable_analysis: bool, enable_update_state: bool, run_id: int, db: DbStorage, turn: int, enable_rag_response: bool = False) -> Table:
    table = Table(title="Executed Command History", show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    if enable_rag_response:
        table.add_column("RAG-time", style="dim")
        table.add_column("RAG-response")
    if enable_analysis:
        table.add_column("ExplTime", style="dim")
        table.add_column("ExplTokens", style="dim")
        table.add_column("Explanation")
    if enable_update_state:
        table.add_column("StateUpdTime", style="dim")
        table.add_column("StateUpdTokens", style="dim")

    for i in range(1, turn+1):
        table.add_row(*db.get_round_data(run_id, i, enable_analysis, enable_update_state, enable_rag_response))

    return table
