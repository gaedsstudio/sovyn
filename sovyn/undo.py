from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UndoMetadata:
    modified: tuple[Path, ...]
    created: tuple[Path, ...]


def describe_last_undo(metadata: UndoMetadata | None) -> str:
    if metadata is None:
        return "No reversible operation recorded."
    changed = len(metadata.modified) + len(metadata.created)
    return f"Last reversible operation covers {changed} paths."
