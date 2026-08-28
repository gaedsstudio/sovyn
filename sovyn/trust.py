from dataclasses import dataclass
from pathlib import Path

from sovyn.storage import Store


@dataclass(frozen=True, slots=True)
class WorkspaceTrust:
    store: Store

    def is_trusted(self, workspace: Path) -> bool:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM trusted_workspaces WHERE path = ?",
                (str(workspace.resolve()),),
            ).fetchone()
        return row is not None

    def trust(self, workspace: Path) -> None:
        with self.store.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO trusted_workspaces (path) VALUES (?)",
                (str(workspace.resolve()),),
            )
            connection.commit()
