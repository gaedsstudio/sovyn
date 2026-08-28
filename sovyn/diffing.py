from dataclasses import dataclass
from pathlib import Path
import difflib


@dataclass(frozen=True, slots=True)
class DiffPreview:
    path: Path
    additions: int
    deletions: int
    preview: str


def preview_write(path: Path, new_content: str, max_lines: int = 24) -> DiffPreview:
    old_content = path.read_text(encoding="utf-8") if path.exists() else ""
    diff = tuple(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
    )
    body = tuple(line for line in diff if not line.startswith(("---", "+++", "@@")))
    additions = sum(1 for line in body if line.startswith("+"))
    deletions = sum(1 for line in body if line.startswith("-"))
    preview = "\n".join(diff[:max_lines])
    return DiffPreview(path=path, additions=additions, deletions=deletions, preview=preview)
