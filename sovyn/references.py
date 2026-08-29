from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path


@unique
class ReferenceKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    GIT_DIFF = "git:diff"


@dataclass(frozen=True, slots=True)
class TaskReference:
    kind: ReferenceKind
    value: str
    path: Path | None = None


def parse_references(request: str, workspace: Path) -> tuple[TaskReference, ...]:
    references: list[TaskReference] = []
    for raw in request.split():
        if not raw.startswith("@"):
            continue
        token = raw[1:].strip()
        if token == "git:diff":
            references.append(TaskReference(ReferenceKind.GIT_DIFF, token))
            continue
        path = (workspace / token).resolve()
        kind = ReferenceKind.DIRECTORY if path.is_dir() else ReferenceKind.FILE
        references.append(TaskReference(kind, token, path))
    return tuple(references)


def reference_context(request: str, workspace: Path) -> str:
    references = parse_references(request, workspace)
    if not references:
        return ""
    lines = ["References:"]
    for item in references:
        match item.kind:
            case ReferenceKind.FILE:
                lines.append(f"- file {item.value}")
            case ReferenceKind.DIRECTORY:
                lines.append(f"- directory {item.value}")
            case ReferenceKind.GIT_DIFF:
                lines.append("- git diff")
    return "\n".join(lines)
