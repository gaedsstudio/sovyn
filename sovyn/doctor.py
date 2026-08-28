from dataclasses import dataclass
from pathlib import Path
import shutil
import sqlite3
import sys

from sovyn.paths import SovynPaths


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    detail: str
    ok: bool


def run_doctor(paths: SovynPaths) -> tuple[DoctorCheck, ...]:
    return (
        DoctorCheck("Python", ".".join(str(part) for part in sys.version_info[:3]), True),
        DoctorCheck("Git", "detected" if shutil.which("git") else "not found", shutil.which("git") is not None),
        DoctorCheck("Ollama", "detected" if shutil.which("ollama") else "not configured", True),
        DoctorCheck("SQLite", sqlite3.sqlite_version, True),
        DoctorCheck("Config", "valid" if paths.config.exists() else "will be created on first run", True),
        DoctorCheck("Workspace", str(Path.cwd()), Path.cwd().exists()),
    )
