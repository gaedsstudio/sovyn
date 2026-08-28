from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Literal

from sovyn.tools import ToolResult


@dataclass(frozen=True, slots=True)
class Store:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        _migrate(connection)
        return connection


def _migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "request TEXT NOT NULL,"
        "result TEXT NOT NULL,"
        "tool_calls INTEGER NOT NULL,"
        "duration_seconds REAL NOT NULL,"
        "created_at TEXT NOT NULL"
        ");"
        "CREATE TABLE IF NOT EXISTS memory ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "category TEXT NOT NULL,"
        "note TEXT NOT NULL,"
        "created_at TEXT NOT NULL"
        ");"
        "CREATE TABLE IF NOT EXISTS trajectory_steps ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id INTEGER NOT NULL,"
        "step_index INTEGER NOT NULL,"
        "tool TEXT NOT NULL,"
        "arguments TEXT NOT NULL,"
        "result_summary TEXT NOT NULL,"
        "classification TEXT NOT NULL,"
        "duration_seconds REAL NOT NULL"
        ");"
        "CREATE TABLE IF NOT EXISTS trusted_workspaces ("
        "path TEXT PRIMARY KEY"
        ");"
        "CREATE TABLE IF NOT EXISTS permission_grants ("
        "action TEXT NOT NULL,"
        "description TEXT NOT NULL,"
        "PRIMARY KEY (action, description)"
        ");"
    )
    connection.commit()


def record_trajectory(
    store: Store,
    session_id: int,
    tools: tuple[ToolResult, ...],
    classification: Literal["deterministic", "agent-required", "user-required"] = "deterministic",
) -> None:
    with store.connect() as connection:
        connection.executemany(
            "INSERT INTO trajectory_steps "
            "(session_id, step_index, tool, arguments, result_summary, classification, duration_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            tuple(
                (session_id, index, tool.name, "{}", tool.summary, classification, 0.0)
                for index, tool in enumerate(tools, start=1)
            ),
        )
        connection.commit()


def trajectory_for_session(store: Store, session_id: int) -> tuple[ToolResult, ...]:
    with store.connect() as connection:
        rows = connection.execute(
            "SELECT tool, result_summary FROM trajectory_steps WHERE session_id = ? ORDER BY step_index",
            (session_id,),
        ).fetchall()
    return tuple(ToolResult(str(row[0]), str(row[1])) for row in rows)


def grant_permission(store: Store, action: str, description: str) -> None:
    with store.connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO permission_grants (action, description) VALUES (?, ?)",
            (action, description),
        )
        connection.commit()


def has_permission_grant(store: Store, action: str, description: str) -> bool:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM permission_grants WHERE action = ? AND description = ?",
            (action, description),
        ).fetchone()
    return row is not None
