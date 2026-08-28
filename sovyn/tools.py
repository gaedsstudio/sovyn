from dataclasses import dataclass
from pathlib import Path
import subprocess

import httpx

IGNORED_DIRECTORIES = {".git", ".next", ".pytest_cache", ".ruff_cache", ".venv", ".venv-gpu", "__pycache__", "node_modules", "outputs"}


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    summary: str


def list_files(workspace: Path) -> ToolResult:
    count = sum(1 for path in workspace.rglob("*") if path.is_file() and not _ignored(path))
    return ToolResult("filesystem.list", f"{count} files indexed")


def read_file(path: Path) -> ToolResult:
    content = path.read_text(encoding="utf-8")
    return ToolResult("filesystem.read", f"{len(content)} characters read")


def write_file(path: Path, content: str) -> ToolResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ToolResult("filesystem.write", f"wrote {path.name}")


def move_file(source: Path, destination: Path) -> ToolResult:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)
    return ToolResult("filesystem.move", f"moved {source.name}")


def delete_file(path: Path) -> ToolResult:
    path.unlink()
    return ToolResult("filesystem.delete", f"deleted {path.name}")


def search_workspace(workspace: Path, term: str) -> ToolResult:
    matches = [path for path in workspace.rglob("*") if path.is_file() and not _ignored(path) and term.lower() in path.name.lower()]
    return ToolResult("workspace.search", f"{len(matches)} filename matches")


def git_status(workspace: Path) -> ToolResult:
    result = subprocess.run(["git", "status", "--short"], cwd=workspace, capture_output=True, text=True, check=False)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return ToolResult("git.status", f"{len(lines)} changed paths")


def git_diff(workspace: Path) -> ToolResult:
    result = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, check=False)
    return ToolResult("git.diff", result.stdout.strip() or "no diff")


def git_log(workspace: Path) -> ToolResult:
    result = subprocess.run(["git", "log", "-5", "--oneline"], cwd=workspace, capture_output=True, text=True, check=False)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return ToolResult("git.log", f"{len(lines)} commits")


def shell_run(workspace: Path, command: tuple[str, ...]) -> ToolResult:
    result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, check=False)
    return ToolResult("shell.run", f"exit {result.returncode}")


def python_run(workspace: Path, code: str) -> ToolResult:
    result = subprocess.run(["python", "-c", code], cwd=workspace, capture_output=True, text=True, check=False)
    return ToolResult("python.run", f"exit {result.returncode}")


def http_get(url: str) -> ToolResult:
    response = httpx.get(url, timeout=30.0)
    return ToolResult("http.get", f"HTTP {response.status_code}")


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRECTORIES for part in path.parts)
