from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sovyn.storage import Store


@dataclass(frozen=True, slots=True)
class UndoEntry:
    path: Path
    existed: bool
    content: str


@dataclass(frozen=True, slots=True)
class UndoBatch:
    id: int
    description: str
    entries: tuple[UndoEntry, ...]


def record_file_snapshot(store: Store, workspace: Path, path: Path, description: str) -> None:
    relative = path.resolve().relative_to(workspace.resolve())
    existed = path.exists()
    content = path.read_text(encoding="utf-8") if existed else ""
    with store.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO undo_batches (description, created_at) VALUES (?, ?)",
            (description, datetime.now(UTC).isoformat()),
        )
        batch_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO undo_entries (batch_id, path, existed, content) VALUES (?, ?, ?, ?)",
            (batch_id, relative.as_posix(), int(existed), content),
        )
        connection.commit()


def latest_undo_id(store: Store) -> int:
    with store.connect() as connection:
        row = connection.execute("SELECT COALESCE(MAX(id), 0) FROM undo_batches").fetchone()
    return int(row[0])


def rename_undo_batches_after(store: Store, batch_id: int, description: str) -> None:
    with store.connect() as connection:
        connection.execute("UPDATE undo_batches SET description = ? WHERE id > ?", (description, batch_id))
        connection.commit()


def restore_last_change(store: Store, workspace: Path) -> tuple[Path, ...]:
    batch = _last_batch(store)
    if batch is None:
        return ()
    changed: list[Path] = []
    root = workspace.resolve()
    for entry in batch.entries:
        path = (root / entry.path).resolve()
        if entry.existed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(entry.content, encoding="utf-8")
        elif path.exists():
            path.unlink()
        changed.append(path)
    with store.connect() as connection:
        connection.execute("DELETE FROM undo_entries WHERE batch_id = ?", (batch.id,))
        connection.execute("DELETE FROM undo_batches WHERE id = ?", (batch.id,))
        connection.commit()
    return tuple(changed)


def describe_last_undo(store: Store | None) -> str:
    if store is None:
        return "No reversible operation recorded."
    batch = _last_batch(store)
    if batch is None:
        return "No reversible operation recorded."
    paths = "\n".join(entry.path.as_posix() for entry in batch.entries)
    return f"Last reversible operation\n\n{batch.description}\n\n{paths}"


def describe_history(store: Store) -> str:
    with store.connect() as connection:
        rows = connection.execute("SELECT description FROM undo_batches ORDER BY id DESC LIMIT 10").fetchall()
    if not rows:
        return "No SOVYN changes recorded."
    lines = ["Recent SOVYN changes", ""]
    lines.extend(f"{index}  {row[0]}" for index, row in enumerate(rows, start=1))
    return "\n".join(lines)


def _last_batch(store: Store) -> UndoBatch | None:
    with store.connect() as connection:
        row = connection.execute("SELECT id, description FROM undo_batches ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        entries = connection.execute(
            "SELECT path, existed, content FROM undo_entries WHERE batch_id = ? ORDER BY id",
            (int(row[0]),),
        ).fetchall()
    return UndoBatch(
        id=int(row[0]),
        description=str(row[1]),
        entries=tuple(UndoEntry(Path(str(entry[0])), bool(entry[1]), str(entry[2])) for entry in entries),
    )
