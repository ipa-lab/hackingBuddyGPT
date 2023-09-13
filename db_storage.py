import sqlite3

class DbStorage:
    def __init__(self, connection_string=":memory:"):
        self.connection_string = connection_string
    
    def connect(self):
        self.db = sqlite3.connect(self.connection_string)
        self.cursor = self.db.cursor()


    def setup_db(self):
        # create tables
        self.cursor.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, model text, context_size INTEGER)")
        self.cursor.execute("CREATE TABLE commands (id INTEGER PRIMARY KEY, name string)")
        self.cursor.execute("CREATE TABLE queries (run_id INTEGER, round INTEGER, cmd_id INTEGER, query TEXT, response TEXT, duration REAL, tokens_query INTEGER, tokens_response INTEGER)")

        # insert commands
        self.cursor.execute("INSERT INTO commands (name) VALUES (?)", ("query_cmd", ))
        self.query_cmd_id = self.cursor.lastrowid

        self.cursor.execute("INSERT INTO commands (name) VALUES (?)", ("analyze_response", ))
        self.analyze_response_id = self.cursor.lastrowid

        self.cursor.execute("INSERT INTO commands (name) VALUES (?)", ("update_state", ))
        self.state_update_id = self.cursor.lastrowid

    def create_new_run(self, model, context_size):
        self.cursor.execute("INSERT INTO runs (model, context_size) VALUES (?, ?)", (model, context_size))
        return self.cursor.lastrowid

    def add_log_query(self, run_id, round, cmd, result, duration=0, tokens_query=0, tokens_response=0):
        self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.query_cmd_id, cmd, result, duration, tokens_query, tokens_response))

    def add_log_analyze_response(self, run_id, round, cmd, result, duration=0, tokens_query=0, tokens_response=0):
        self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.analyze_response_id, cmd, result, duration, tokens_query, tokens_response))

    def add_log_update_state(self, run_id, round, cmd, result, duration=0, tokens_query=0, tokens_response=0):
        self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.state_update_id, cmd, result, duration, tokens_query, tokens_response))


    def get_round_data(self, run_id, round):
        rows = self.cursor.execute("select cmd_id, query, response, duration, tokens_query, tokens_response from queries where run_id = ? and round = ?", (run_id, round)).fetchall()

        for row in rows:
            if row[0] == self.query_cmd_id:
                cmd = row[1]
                size_resp = str(len(row[2]))
                duration = str(row[3])
                tokens = str(row[4]) + "/" + str(row[5])
            if row[0] == self.analyze_response_id:
                reason = row[2]
                analyze_time = str(row[3])
                analyze_token = str(row[4]) + "/" + str(row[5])

        result = [duration, tokens, cmd, size_resp, analyze_time, analyze_token, reason]
        return result

    def get_cmd_history(self, run_id):
        rows = self.cursor.execute("select query, response from queries where run_id = ? and cmd_id = ? order by round asc", (run_id, self.query_cmd_id)).fetchall()

        result = []

        for row in rows:
            result.append([row[0], row[1]])

        return result