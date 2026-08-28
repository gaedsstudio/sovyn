from dataclasses import dataclass
from datetime import UTC, datetime

from sovyn.storage import Store


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: int
    request: str
    result: str
    tool_calls: int
    duration_seconds: float
    created_at: str


def create_session(store: Store, request: str, result: str, tool_calls: int, duration_seconds: float) -> int:
    with store.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO sessions (request, result, tool_calls, duration_seconds, created_at) VALUES (?, ?, ?, ?, ?)",
            (request, result, tool_calls, duration_seconds, datetime.now(UTC).isoformat()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_sessions(store: Store) -> tuple[SessionRecord, ...]:
    with store.connect() as connection:
        rows = connection.execute(
            "SELECT id, request, result, tool_calls, duration_seconds, created_at FROM sessions ORDER BY id DESC"
        ).fetchall()
    return tuple(SessionRecord(int(row[0]), str(row[1]), str(row[2]), int(row[3]), float(row[4]), str(row[5])) for row in rows)


def get_session(store: Store, session_id: int) -> SessionRecord | None:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT id, request, result, tool_calls, duration_seconds, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return SessionRecord(int(row[0]), str(row[1]), str(row[2]), int(row[3]), float(row[4]), str(row[5]))
