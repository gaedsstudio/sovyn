from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


@dataclass(frozen=True, slots=True)
class PathSafetyError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def resolve_workspace_path(workspace: Path, raw_path: str) -> Path:
    if raw_path.startswith(("\\\\", "//")):
        raise PathSafetyError("UNC or network paths are not allowed")
    candidate_text = raw_path.strip()
    windows_path = PureWindowsPath(candidate_text)
    if windows_path.drive:
        candidate = Path(candidate_text)
    else:
        candidate = workspace / candidate_text
    workspace_root = workspace.resolve()
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise PathSafetyError("Path escapes the trusted workspace") from exc
    existing_parent = resolved.parent
    if existing_parent.exists():
        real_parent = existing_parent.resolve(strict=True)
        try:
            real_parent.relative_to(workspace_root)
        except ValueError as exc:
            raise PathSafetyError("Path parent resolves outside the trusted workspace") from exc
    return resolved
