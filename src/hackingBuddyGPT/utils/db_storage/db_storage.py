import sqlite3

from hackingBuddyGPT.utils.configurable import configurable, parameter


@configurable("db_storage", "Stores the results of the experiments in a SQLite database")
class DbStorage:
    def __init__(self, connection_string: str = parameter(desc="sqlite3 database connection string for logs", default=":memory:")):
        self.connection_string = connection_string

    def init(self):
        self.connect()
        self.setup_db()

    def connect(self):
        self.db = sqlite3.connect(self.connection_string)
        self.cursor = self.db.cursor()

    def insert_or_select_cmd(self, name: str) -> int:
        results = self.cursor.execute("SELECT id, name FROM commands WHERE name = ?", (name,)).fetchall()

        if len(results) == 0:
            self.cursor.execute("INSERT INTO commands (name) VALUES (?)", (name,))
            return self.cursor.lastrowid
        elif len(results) == 1:
            return results[0][0]
        else:
            print("this should not be happening: " + str(results))
            return -1

    def setup_db(self):
        # create tables
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, model text, context_size INTEGER, state TEXT, tag TEXT, started_at text, stopped_at text, rounds INTEGER, configuration TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS commands (id INTEGER PRIMARY KEY, name string unique)")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS queries (run_id INTEGER, round INTEGER, cmd_id INTEGER, query TEXT, response TEXT, duration REAL, tokens_query INTEGER, tokens_response INTEGER, prompt TEXT, answer TEXT)")

        # insert commands
        self.query_cmd_id = self.insert_or_select_cmd('query_cmd')
        self.analyze_response_id = self.insert_or_select_cmd('analyze_response')
        self.state_update_id = self.insert_or_select_cmd('update_state')

    def create_new_run(self, model, context_size, tag):
        self.cursor.execute(
            "INSERT INTO runs (model, context_size, state, tag, started_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (model, context_size, "in progress", tag))
        return self.cursor.lastrowid

    def add_log_query(self, run_id, round, cmd, result, answer):
        self.cursor.execute(
            "INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response, prompt, answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
            run_id, round, self.query_cmd_id, cmd, result, answer.duration, answer.tokens_query, answer.tokens_response,
            answer.prompt, answer.answer))

    def add_log_analyze_response(self, run_id, round, cmd, result, answer):
        self.cursor.execute(
            "INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response, prompt, answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, round, self.analyze_response_id, cmd, result, answer.duration, answer.tokens_query,
             answer.tokens_response, answer.prompt, answer.answer))

    def add_log_update_state(self, run_id, round, cmd, result, answer):

        if answer is not None:
            self.cursor.execute(
                "INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response, prompt, answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, round, self.state_update_id, cmd, result, answer.duration, answer.tokens_query,
                 answer.tokens_response, answer.prompt, answer.answer))
        else:
            self.cursor.execute(
                "INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response, prompt, answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, round, self.state_update_id, cmd, result, 0, 0, 0, '', ''))

    def get_round_data(self, run_id, round, explanation, status_update):
        rows = self.cursor.execute(
            "select cmd_id, query, response, duration, tokens_query, tokens_response from queries where run_id = ? and round = ?",
            (run_id, round)).fetchall()
        if len(rows) == 0:
            return []

        for row in rows:
            if row[0] == self.query_cmd_id:
                cmd = row[1]
                size_resp = str(len(row[2]))
                duration = f"{row[3]:.4f}"
                tokens = f"{row[4]}/{row[5]}"
            if row[0] == self.analyze_response_id and explanation:
                reason = row[2]
                analyze_time = f"{row[3]:.4f}"
                analyze_token = f"{row[4]}/{row[5]}"
            if row[0] == self.state_update_id and status_update:
                state_time = f"{row[3]:.4f}"
                state_token = f"{row[4]}/{row[5]}"

        result = [duration, tokens, cmd, size_resp]
        if explanation:
            result += [analyze_time, analyze_token, reason]
        if status_update:
            result += [state_time, state_token]
        return result

    def get_max_round_for(self, run_id):
        run = self.cursor.execute("select max(round) from queries where run_id = ?", (run_id,)).fetchone()
        if run is not None:
            return run[0]
        else:
            return None

    def get_run_data(self, run_id):
        run = self.cursor.execute("select * from runs where id = ?", (run_id,)).fetchone()
        if run is not None:
            return run[1], run[2], run[4], run[3], run[7], run[8]
        else:
            return None

    def get_log_overview(self):
        result = {}

        max_rounds = self.cursor.execute("select run_id, max(round) from queries group by run_id").fetchall()
        for row in max_rounds:
            state = self.cursor.execute("select state from runs where id = ?", (row[0],)).fetchone()
            last_cmd = self.cursor.execute("select query from queries where run_id = ? and round = ?",
                                           (row[0], row[1])).fetchone()

            result[row[0]] = {
                "max_round": int(row[1]) + 1,
                "state": state[0],
                "last_cmd": last_cmd[0]
            }

        return result

    def get_cmd_history(self, run_id):
        rows = self.cursor.execute(
            "select query, response from queries where run_id = ? and cmd_id = ? order by round asc",
            (run_id, self.query_cmd_id)).fetchall()

        result = []

        for row in rows:
            result.append([row[0], row[1]])

        return result

    def run_was_success(self, run_id, round):
        self.cursor.execute("update runs set state=?,stopped_at=datetime('now'), rounds=? where id = ?",
                            ("got root", round, run_id))
        self.db.commit()

    def run_was_failure(self, run_id, round):
        self.cursor.execute("update runs set state=?, stopped_at=datetime('now'), rounds=? where id = ?",
                            ("reached max runs", round, run_id))
        self.db.commit()

    def commit(self):
        self.db.commit()
