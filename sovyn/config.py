from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
import tomllib

from sovyn.paths import SovynPaths


@unique
class PermissionPolicy(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class ModelSettings:
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class AgentSettings:
    max_steps: int


@dataclass(frozen=True, slots=True)
class PermissionSettings:
    read_files: PermissionPolicy
    write_files: PermissionPolicy
    shell: PermissionPolicy
    delete_files: PermissionPolicy
    git_commit: PermissionPolicy


@dataclass(frozen=True, slots=True)
class UiSettings:
    animations: bool
    timestamps: bool


@dataclass(frozen=True, slots=True)
class SovynConfig:
    model: ModelSettings
    agent: AgentSettings
    permissions: PermissionSettings
    ui: UiSettings


DEFAULT_CONFIG = SovynConfig(
    model=ModelSettings(provider="mock", model="mock-local"),
    agent=AgentSettings(max_steps=30),
    permissions=PermissionSettings(
        read_files=PermissionPolicy.ALLOW,
        write_files=PermissionPolicy.ASK,
        shell=PermissionPolicy.ASK,
        delete_files=PermissionPolicy.ASK,
        git_commit=PermissionPolicy.ASK,
    ),
    ui=UiSettings(animations=True, timestamps=False),
)


def load_config(paths: SovynPaths) -> SovynConfig:
    if not paths.config.exists():
        return DEFAULT_CONFIG
    raw = tomllib.loads(paths.config.read_text(encoding="utf-8"))
    return SovynConfig(
        model=ModelSettings(
            provider=str(raw.get("model", {}).get("provider", DEFAULT_CONFIG.model.provider)),
            model=str(raw.get("model", {}).get("model", DEFAULT_CONFIG.model.model)),
        ),
        agent=AgentSettings(max_steps=int(raw.get("agent", {}).get("max_steps", DEFAULT_CONFIG.agent.max_steps))),
        permissions=PermissionSettings(
            read_files=PermissionPolicy(raw.get("permissions", {}).get("read_files", DEFAULT_CONFIG.permissions.read_files)),
            write_files=PermissionPolicy(raw.get("permissions", {}).get("write_files", DEFAULT_CONFIG.permissions.write_files)),
            shell=PermissionPolicy(raw.get("permissions", {}).get("shell", DEFAULT_CONFIG.permissions.shell)),
            delete_files=PermissionPolicy(raw.get("permissions", {}).get("delete_files", DEFAULT_CONFIG.permissions.delete_files)),
            git_commit=PermissionPolicy(raw.get("permissions", {}).get("git_commit", DEFAULT_CONFIG.permissions.git_commit)),
        ),
        ui=UiSettings(
            animations=bool(raw.get("ui", {}).get("animations", DEFAULT_CONFIG.ui.animations)),
            timestamps=bool(raw.get("ui", {}).get("timestamps", DEFAULT_CONFIG.ui.timestamps)),
        ),
    )


def write_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "[model]",
                'provider = "mock"',
                'model = "mock-local"',
                "",
                "[agent]",
                "max_steps = 30",
                "",
                "[permissions]",
                'read_files = "allow"',
                'write_files = "ask"',
                'shell = "ask"',
                'delete_files = "ask"',
                'git_commit = "ask"',
                "",
                "[ui]",
                "animations = true",
                "timestamps = false",
                "",
            )
        ),
        encoding="utf-8",
    )
