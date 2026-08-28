from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import sqlite3
import sys

from sovyn.config import SovynConfig
from sovyn.paths import SovynPaths
from sovyn.provider_init import ProviderResolution, ProviderStatus
from sovyn.storage import Store
from sovyn.trust import WorkspaceTrust


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    detail: str
    ok: bool


def run_doctor(paths: SovynPaths, config: SovynConfig, provider: ProviderResolution) -> tuple[DoctorCheck, ...]:
    trusted = WorkspaceTrust(Store(paths.database)).is_trusted(paths.workspace)
    return (
        DoctorCheck("Python", ".".join(str(part) for part in sys.version_info[:3]), True),
        DoctorCheck("Git", "detected" if shutil.which("git") else "not found", shutil.which("git") is not None),
        DoctorCheck("Ollama", "detected" if shutil.which("ollama") else "not configured", True),
        DoctorCheck("SQLite", sqlite3.sqlite_version, True),
        DoctorCheck("Config", "valid" if paths.config.exists() else "will be created on first run", True),
        DoctorCheck("Workspace", str(Path.cwd()), Path.cwd().exists()),
        DoctorCheck("Workspace trust", "trusted" if trusted else "not trusted", trusted),
        DoctorCheck("Provider", config.model.provider, provider.status is ProviderStatus.READY),
        DoctorCheck("Model", config.model.model, provider.status is ProviderStatus.READY),
        DoctorCheck("Credentials", _credential_detail(config), True),
    )


def _credential_detail(config: SovynConfig) -> str:
    match config.model.provider:
        case "openai" | "openai-compatible":
            return "configured" if "OPENAI_API_KEY" in os.environ else "not configured"
        case "anthropic":
            return "configured" if "ANTHROPIC_API_KEY" in os.environ else "not configured"
        case _:
            return "not required"
