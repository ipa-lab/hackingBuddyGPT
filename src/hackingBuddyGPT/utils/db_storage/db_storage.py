from dataclasses import dataclass, field
from dataclasses_json import config, dataclass_json
import datetime
import sqlite3
from typing import Literal, Optional, Union

from hackingBuddyGPT.utils.configurable import Global, configurable, parameter


timedelta_metadata = config(encoder=lambda td: td.total_seconds(), decoder=lambda seconds: datetime.timedelta(seconds=seconds))
datetime_metadata = config(encoder=lambda dt: dt.isoformat(), decoder=lambda iso: datetime.datetime.fromisoformat(iso))
optional_datetime_metadata = config(encoder=lambda dt: dt.isoformat() if dt else None, decoder=lambda iso: datetime.datetime.fromisoformat(iso) if iso else None)


StreamAction = Literal["append"]


@dataclass_json
@dataclass
class Run:
    id: int
    model: str
    state: str
    tag: str
    started_at: datetime.datetime = field(metadata=datetime_metadata)
    stopped_at: Optional[datetime.datetime] = field(metadata=optional_datetime_metadata)
    configuration: str


@dataclass_json
@dataclass
class Section:
    run_id: int
    id: int
    name: str
    from_message: int
    to_message: int
    duration: datetime.timedelta = field(metadata=timedelta_metadata)


@dataclass_json
@dataclass
class Message:
    run_id: int
    id: int
    version: int
    conversation: str
    role: str
    content: str
    duration: datetime.timedelta = field(metadata=timedelta_metadata)
    tokens_query: int
    tokens_response: int


@dataclass_json
@dataclass
class MessageStreamPart:
    id: int
    run_id: int
    message_id: int
    action: StreamAction
    content: str


@dataclass_json
@dataclass
class ToolCall:
    run_id: int
    message_id: int
    id: str
    version: int
    function_name: str
    arguments: str
    state: str
    result_text: str
    duration: datetime.timedelta = field(metadata=timedelta_metadata)


@dataclass_json
@dataclass
class ToolCallStreamPart:
    id: int
    run_id: int
    message_id: int
    tool_call_id: str
    field: Literal["arguments", "result"]
    action: StreamAction
    content: str


LogTypes = Union[Run, Section, Message, MessageStreamPart, ToolCall, ToolCallStreamPart]


@configurable("db_storage", "Stores the results of the experiments in a SQLite database")
class RawDbStorage:
    def __init__(
        self, connection_string: str = parameter(desc="sqlite3 database connection string for logs", default="wintermute.sqlite3")
    ):
        self.connection_string = connection_string

    def init(self):
        self.connect()
        self.setup_db()

    def connect(self):
        self.db = sqlite3.connect(self.connection_string, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def setup_db(self):
        # create tables
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                model text,
                state TEXT,
                tag TEXT,
                started_at text,
                stopped_at text,
                configuration TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sections (
                run_id INTEGER,
                id INTEGER,
                name TEXT,
                from_message INTEGER,
                to_message INTEGER,
                duration REAL,
                PRIMARY KEY (run_id, id),
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                run_id INTEGER,
                conversation TEXT,
                id INTEGER,
                version INTEGER DEFAULT 0,
                role TEXT,
                content TEXT,
                duration REAL,
                tokens_query INTEGER,
                tokens_response INTEGER,
                PRIMARY KEY (run_id, id),
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                run_id INTEGER,
                message_id INTEGER,
                id TEXT,
                version INTEGER DEFAULT 0,
                function_name TEXT,
                arguments TEXT,
                state TEXT,
                result_text TEXT,
                duration REAL,
                PRIMARY KEY (run_id, message_id, id),
                FOREIGN KEY (run_id, message_id) REFERENCES messages (run_id, id)
            )
        """)

    def get_runs(self) -> list[Run]:
        def deserialize(row):
            row = dict(row)
            row["started_at"] = datetime.datetime.fromisoformat(row["started_at"])
            row["stopped_at"] = datetime.datetime.fromisoformat(row["stopped_at"]) if row["stopped_at"] else None
            return row

        self.cursor.execute("SELECT * FROM runs")
        return [Run(**deserialize(row)) for row in self.cursor.fetchall()]

    def get_sections_by_run(self, run_id: int) -> list[Section]:
        def deserialize(row):
            row = dict(row)
            row["duration"] = datetime.timedelta(seconds=row["duration"])
            return row

        self.cursor.execute("SELECT * FROM sections WHERE run_id = ?", (run_id,))
        return [Section(**deserialize(row)) for row in self.cursor.fetchall()]

    def get_messages_by_run(self, run_id: int) -> list[Message]:
        def deserialize(row):
            row = dict(row)
            row["duration"] = datetime.timedelta(seconds=row["duration"])
            return row

        self.cursor.execute("SELECT * FROM messages WHERE run_id = ?", (run_id,))
        return [Message(**deserialize(row)) for row in self.cursor.fetchall()]

    def get_tool_calls_by_run(self, run_id: int) -> list[ToolCall]:
        def deserialize(row):
            row = dict(row)
            row["duration"] = datetime.timedelta(seconds=row["duration"])
            return row

        self.cursor.execute("SELECT * FROM tool_calls WHERE run_id = ?", (run_id,))
        return [ToolCall(**deserialize(row)) for row in self.cursor.fetchall()]

    def create_run(self, model: str, tag: str, started_at: datetime.datetime, configuration: str) -> int:
        self.cursor.execute(
            "INSERT INTO runs (model, state, tag, started_at, configuration) VALUES (?, ?, ?, ?, ?)",
            (model, "in progress", tag, started_at, configuration),
        )
        return self.cursor.lastrowid

    def add_message(self, run_id: int, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        self.cursor.execute(
            "INSERT INTO messages (run_id, conversation, id, role, content, tokens_query, tokens_response, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, conversation, message_id, role, content, tokens_query, tokens_response, duration.total_seconds())
        )

    def add_or_update_message(self, run_id: int, message_id: int, conversation: Optional[str], role: str, content: str, tokens_query: int, tokens_response: int, duration: datetime.timedelta):
        self.cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE run_id = ? AND id = ?",
            (run_id, message_id),
        )
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute(
                "INSERT INTO messages (run_id, conversation, id, role, content, tokens_query, tokens_response, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, conversation, message_id, role, content, tokens_query, tokens_response, duration.total_seconds()),
            )
        else:
            if len(content) > 0:
                self.cursor.execute(
                    "UPDATE messages SET conversation = ?, role = ?, content = ?, tokens_query = ?, tokens_response = ?, duration = ? WHERE run_id = ? AND id = ?",
                    (conversation, role, content, tokens_query, tokens_response, duration.total_seconds(), run_id, message_id),
                )
            else:
                self.cursor.execute(
                    "UPDATE messages SET conversation = ?, role = ?, tokens_query = ?, tokens_response = ?, duration = ? WHERE run_id = ? AND id = ?",
                    (conversation, role, tokens_query, tokens_response, duration.total_seconds(), run_id, message_id),
                )

    def add_section(self, run_id: int, section_id: int, name: str, from_message: int, to_message: int, duration: datetime.timedelta):
        self.cursor.execute(
            "INSERT OR REPLACE INTO sections (run_id, id, name, from_message, to_message, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, section_id, name, from_message, to_message, duration.total_seconds())
        )

    def add_tool_call(self, run_id: int, message_id: int, tool_call_id: str, function_name: str, arguments: str, result_text: str, duration: datetime.timedelta):
        self.cursor.execute(
            "INSERT INTO tool_calls (run_id, message_id, id, function_name, arguments, result_text, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, message_id, tool_call_id, function_name, arguments, result_text, duration.total_seconds()),
        )

    def handle_message_update(self, run_id: int, message_id: int, action: StreamAction, content: str):
        if action != "append":
            raise ValueError("unsupported action" + action)
        self.cursor.execute(
            "UPDATE messages SET content = content || ?, version = version + 1 WHERE run_id = ? AND id = ?",
            (content, run_id, message_id),
        )

    def finalize_message(self, run_id: int, message_id: int, tokens_query: int, tokens_response: int, duration: datetime.timedelta, overwrite_finished_message: Optional[str] = None):
        if overwrite_finished_message:
            self.cursor.execute(
                "UPDATE messages SET content = ?, tokens_query = ?, tokens_response = ?, duration = ? WHERE run_id = ? AND id = ?",
                (overwrite_finished_message, tokens_query, tokens_response, duration.total_seconds(), run_id, message_id),
            )
        else:
            self.cursor.execute(
                "UPDATE messages SET tokens_query = ?, tokens_response = ?, duration = ? WHERE run_id = ? AND id = ?",
                (tokens_query, tokens_response, duration.total_seconds(), run_id, message_id),
            )

    def update_run(self, run_id: int, model: str, state: str, tag: str, started_at: datetime.datetime, stopped_at: datetime.datetime, configuration: str):
        self.cursor.execute(
            "UPDATE runs SET model = ?, state = ?, tag = ?, started_at = ?, stopped_at = ?, configuration = ? WHERE id = ?",
            (model, state, tag, started_at, stopped_at, configuration, run_id),
        )

    def run_was_success(self, run_id):
        self.cursor.execute(
            "update runs set state=?,stopped_at=datetime('now') where id = ?",
            ("got root", run_id),
        )
        self.db.commit()

    def run_was_failure(self, run_id: int, reason: str):
        self.cursor.execute(
            "update runs set state=?, stopped_at=datetime('now') where id = ?",
            (reason, run_id),
        )
        self.db.commit()


DbStorage = Global(RawDbStorage)
