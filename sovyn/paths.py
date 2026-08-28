from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SovynPaths:
    root: Path
    config: Path
    database: Path
    memory: Path
    workflows: Path
    sessions: Path
    logs: Path
    cache: Path
    workspace: Path

    def ensure(self) -> None:
        for path in (self.root, self.memory, self.workflows, self.sessions, self.logs, self.cache):
            path.mkdir(parents=True, exist_ok=True)


def default_paths(home: Path | None = None, workspace: Path | None = None) -> SovynPaths:
    root = (home or Path.home()) / ".sovyn"
    workspace_root = workspace or Path.cwd()
    return SovynPaths(
        root=root,
        config=root / "config.toml",
        database=root / "sovyn.db",
        memory=root / "memory",
        workflows=root / "workflows",
        sessions=root / "sessions",
        logs=root / "logs",
        cache=root / "cache",
        workspace=workspace_root,
    )
