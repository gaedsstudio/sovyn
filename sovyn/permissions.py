from dataclasses import dataclass
from enum import StrEnum, unique

from sovyn.config import PermissionPolicy, PermissionSettings


@unique
class ActionKind(StrEnum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    SHELL = "shell"
    DELETE_FILES = "delete_files"
    GIT_COMMIT = "git_commit"


@unique
class PermissionDecision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    action: ActionKind
    description: str
    destructive: bool = False


def decide_permission(settings: PermissionSettings, request: PermissionRequest, interactive: bool) -> PermissionDecision:
    if request.destructive:
        return PermissionDecision.ASK if interactive else PermissionDecision.BLOCK
    policy = PermissionPolicy(getattr(settings, request.action.value))
    match policy:
        case PermissionPolicy.ALLOW:
            return PermissionDecision.ALLOW
        case PermissionPolicy.ASK:
            return PermissionDecision.ASK if interactive else PermissionDecision.BLOCK
        case PermissionPolicy.BLOCK:
            return PermissionDecision.BLOCK
