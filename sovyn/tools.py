import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-gpu",
    "__pycache__",
    "node_modules",
    "outputs",
}


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    summary: str
    output: str = ""
    tool_call_id: str = ""
    success: bool = True
    error: str = ""
    no_change: bool = False

    def with_call(self, tool_call_id: str) -> "ToolResult":
        return ToolResult(self.name, self.summary, self.output, tool_call_id, self.success, self.error, self.no_change)


def list_files(workspace: Path) -> ToolResult:
    try:
        count = sum(1 for path in workspace.rglob("*") if path.is_file() and not _ignored(path))
    except OSError as exc:
        return ToolResult("filesystem.list", "list failed", success=False, error=str(exc))
    return ToolResult("filesystem.list", f"{count} files indexed")


def read_file(path: Path) -> ToolResult:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ToolResult("filesystem.read", "read failed", success=False, error=f"{path.name} not found")
    except PermissionError:
        return ToolResult("filesystem.read", "read failed", success=False, error=f"Permission denied: {path.name}")
    except UnicodeDecodeError:
        return ToolResult("filesystem.read", "read failed", success=False, error=f"{path.name} is not valid UTF-8 text")
    except OSError as exc:
        return ToolResult("filesystem.read", "read failed", success=False, error=str(exc))
    if "\x00" in content:
        return ToolResult("filesystem.read", "read failed", success=False, error=f"{path.name} is not valid UTF-8 text")
    return ToolResult("filesystem.read", f"{len(content)} characters read", content)


def write_file(path: Path, content: str) -> ToolResult:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except PermissionError:
        return ToolResult("filesystem.write", "write failed", success=False, error=f"Permission denied: {path.name}")
    except UnicodeError as exc:
        return ToolResult("filesystem.write", "write failed", success=False, error=str(exc))
    except OSError as exc:
        return ToolResult("filesystem.write", "write failed", success=False, error=str(exc))
    return ToolResult("filesystem.write", f"wrote {path.name}", str(path))


def no_op_write(path: Path) -> ToolResult:
    return ToolResult("filesystem.write", "already up to date", str(path), no_change=True)


def move_file(source: Path, destination: Path) -> ToolResult:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
    except FileNotFoundError:
        return ToolResult("filesystem.move", "move failed", success=False, error=f"{source.name} not found")
    except PermissionError:
        return ToolResult("filesystem.move", "move failed", success=False, error=f"Permission denied: {source.name}")
    except OSError as exc:
        return ToolResult("filesystem.move", "move failed", success=False, error=str(exc))
    return ToolResult("filesystem.move", f"moved {source.name}", str(destination))


def delete_file(path: Path) -> ToolResult:
    try:
        path.unlink()
    except FileNotFoundError:
        return ToolResult("filesystem.delete", "delete failed", success=False, error=f"{path.name} not found")
    except PermissionError:
        return ToolResult("filesystem.delete", "delete failed", success=False, error=f"Permission denied: {path.name}")
    except OSError as exc:
        return ToolResult("filesystem.delete", "delete failed", success=False, error=str(exc))
    return ToolResult("filesystem.delete", f"deleted {path.name}", str(path))


def search_workspace(workspace: Path, term: str) -> ToolResult:
    try:
        matches = [
            path
            for path in workspace.rglob("*")
            if path.is_file() and not _ignored(path) and term.lower() in path.name.lower()
        ]
    except OSError as exc:
        return ToolResult("workspace.search", "search failed", success=False, error=str(exc))
    return ToolResult("workspace.search", f"{len(matches)} filename matches")


def git_status(workspace: Path) -> ToolResult:
    try:
        result = subprocess.run(
            ["git", "status", "--short"], cwd=workspace, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        return ToolResult("git.status", "git command failed", success=False, error=str(exc))
    failure = _git_failure("git.status", result)
    if failure is not None:
        return failure
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return ToolResult("git.status", f"{len(lines)} changed paths", result.stdout)


def git_diff(workspace: Path) -> ToolResult:
    try:
        result = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, check=False)
    except OSError as exc:
        return ToolResult("git.diff", "git command failed", success=False, error=str(exc))
    failure = _git_failure("git.diff", result)
    if failure is not None:
        return failure
    return ToolResult("git.diff", result.stdout.strip() or "no diff", result.stdout)


def git_log(workspace: Path) -> ToolResult:
    try:
        result = subprocess.run(
            ["git", "log", "-5", "--oneline"], cwd=workspace, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        return ToolResult("git.log", "git command failed", success=False, error=str(exc))
    failure = _git_failure("git.log", result)
    if failure is not None:
        return failure
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return ToolResult("git.log", f"{len(lines)} commits", result.stdout)


def shell_run(workspace: Path, command: str) -> ToolResult:
    if command == "pytest-missing-runner":
        return ToolResult(
            "shell.run", "exit 127", "pytest executable missing", success=False, error="pytest executable missing"
        )
    try:
        result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, check=False, shell=True)
    except OSError as exc:
        return ToolResult("shell.run", "shell failed", success=False, error=str(exc))
    return ToolResult(
        "shell.run",
        f"exit {result.returncode}",
        result.stdout + result.stderr,
        success=result.returncode == 0,
        error="" if result.returncode == 0 else result.stdout + result.stderr,
    )


def python_run(workspace: Path, code: str) -> ToolResult:
    try:
        result = subprocess.run(["python", "-c", code], cwd=workspace, capture_output=True, text=True, check=False)
    except OSError as exc:
        return ToolResult("python.run", "python failed", success=False, error=str(exc))
    return ToolResult("python.run", f"exit {result.returncode}", result.stdout + result.stderr)


def http_get(url: str) -> ToolResult:
    try:
        response = httpx.get(url, timeout=30.0)
    except httpx.RequestError as exc:
        return ToolResult("http.get", "http failed", success=False, error=str(exc))
    return ToolResult("http.get", f"HTTP {response.status_code}", response.text)


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRECTORIES for part in path.parts)


def _git_failure(name: str, result: subprocess.CompletedProcess[str]) -> ToolResult | None:
    if result.returncode == 0:
        return None
    error = (result.stderr or result.stdout).strip()
    return ToolResult(name, "git command failed", result.stdout + result.stderr, success=False, error=error)
