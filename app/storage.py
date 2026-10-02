import sqlite3
from pathlib import Path
from threading import Lock


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = Lock()
        self._init()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                  ON messages(conversation_id, id);

                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'processing',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def add_message(self, conversation_id: str, role: str, content: str):
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )

    def history(self, conversation_id: str, limit: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id=?
                ORDER BY id DESC LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def claim_event(self, event_id: str) -> bool:
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    "INSERT INTO processed_events(event_id, status) VALUES (?, 'processing')",
                    (event_id,),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def complete_event(self, event_id: str):
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE processed_events SET status='done' WHERE event_id=?",
                (event_id,),
            )

    def release_event(self, event_id: str):
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM processed_events WHERE event_id=? AND status='processing'",
                (event_id,),
            )
