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
    primary: str = ""
    fallback: str = ""
    thinking: bool = False


@dataclass(frozen=True, slots=True)
class AgentSettings:
    max_steps: int
    context_budget: int
    tool_output_budget: int
    file_content_budget: int


@dataclass(frozen=True, slots=True)
class PermissionSettings:
    read_files: PermissionPolicy
    write_files: PermissionPolicy
    shell: PermissionPolicy
    network_read: PermissionPolicy
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
    model=ModelSettings(provider="mock", model="mock-local", primary="", fallback="", thinking=False),
    agent=AgentSettings(max_steps=30, context_budget=12000, tool_output_budget=4000, file_content_budget=8000),
    permissions=PermissionSettings(
        read_files=PermissionPolicy.ALLOW,
        write_files=PermissionPolicy.ASK,
        shell=PermissionPolicy.ASK,
        network_read=PermissionPolicy.ASK,
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
            primary=str(raw.get("model", {}).get("primary", DEFAULT_CONFIG.model.primary)),
            fallback=str(raw.get("model", {}).get("fallback", DEFAULT_CONFIG.model.fallback)),
            thinking=bool(raw.get("model", {}).get("thinking", DEFAULT_CONFIG.model.thinking)),
        ),
        agent=AgentSettings(
            max_steps=int(raw.get("agent", {}).get("max_steps", DEFAULT_CONFIG.agent.max_steps)),
            context_budget=int(raw.get("agent", {}).get("context_budget", DEFAULT_CONFIG.agent.context_budget)),
            tool_output_budget=int(raw.get("agent", {}).get("tool_output_budget", DEFAULT_CONFIG.agent.tool_output_budget)),
            file_content_budget=int(raw.get("agent", {}).get("file_content_budget", DEFAULT_CONFIG.agent.file_content_budget)),
        ),
        permissions=PermissionSettings(
            read_files=PermissionPolicy(raw.get("permissions", {}).get("read_files", DEFAULT_CONFIG.permissions.read_files)),
            write_files=PermissionPolicy(raw.get("permissions", {}).get("write_files", DEFAULT_CONFIG.permissions.write_files)),
            shell=PermissionPolicy(raw.get("permissions", {}).get("shell", DEFAULT_CONFIG.permissions.shell)),
            network_read=PermissionPolicy(raw.get("permissions", {}).get("network_read", DEFAULT_CONFIG.permissions.network_read)),
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
                'primary = ""',
                'fallback = ""',
                "thinking = false",
                "",
                "[agent]",
                "max_steps = 30",
                "context_budget = 12000",
                "tool_output_budget = 4000",
                "file_content_budget = 8000",
                "",
                "[permissions]",
                'read_files = "allow"',
                'write_files = "ask"',
                'shell = "ask"',
                'network_read = "ask"',
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


def write_config(path: Path, config: SovynConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "[model]",
                f'provider = "{config.model.provider}"',
                f'model = "{config.model.model}"',
                f'primary = "{config.model.primary}"',
                f'fallback = "{config.model.fallback}"',
                f"thinking = {str(config.model.thinking).lower()}",
                "",
                "[agent]",
                f"max_steps = {config.agent.max_steps}",
                f"context_budget = {config.agent.context_budget}",
                f"tool_output_budget = {config.agent.tool_output_budget}",
                f"file_content_budget = {config.agent.file_content_budget}",
                "",
                "[permissions]",
                f'read_files = "{config.permissions.read_files.value}"',
                f'write_files = "{config.permissions.write_files.value}"',
                f'shell = "{config.permissions.shell.value}"',
                f'network_read = "{config.permissions.network_read.value}"',
                f'delete_files = "{config.permissions.delete_files.value}"',
                f'git_commit = "{config.permissions.git_commit.value}"',
                "",
                "[ui]",
                f"animations = {str(config.ui.animations).lower()}",
                f"timestamps = {str(config.ui.timestamps).lower()}",
                "",
            )
        ),
        encoding="utf-8",
    )
