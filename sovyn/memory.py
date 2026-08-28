from dataclasses import dataclass
from datetime import UTC, datetime

from sovyn.storage import Store


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: int
    category: str
    note: str


def add_memory(store: Store, category: str, note: str) -> int:
    with store.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO memory (category, note, created_at) VALUES (?, ?, ?)",
            (category, note, datetime.now(UTC).isoformat()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_memory(store: Store) -> tuple[MemoryRecord, ...]:
    with store.connect() as connection:
        rows = connection.execute("SELECT id, category, note FROM memory ORDER BY id").fetchall()
    return tuple(MemoryRecord(int(row[0]), str(row[1]), str(row[2])) for row in rows)


def forget_memory(store: Store, memory_id: int) -> None:
    with store.connect() as connection:
        connection.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        connection.commit()
