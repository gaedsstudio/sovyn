from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from typing import assert_never
from urllib.parse import urlparse

from sovyn.diffing import preview_write
from sovyn.interaction import Approval, Interaction
from sovyn.path_safety import PathSafetyError, resolve_workspace_path
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.shell_safety import assess_shell_command
from sovyn.tool_protocol import JsonValue, ToolCall
from sovyn.tools import (
    ToolResult,
    git_diff,
    git_log,
    git_status,
    http_get,
    list_files,
    read_file,
    search_workspace,
    shell_run,
    write_file,
)


@unique
class SchemaType(StrEnum):
    STRING = "string"


@dataclass(frozen=True, slots=True)
class ToolArgument:
    name: str
    schema_type: SchemaType
    required: bool = True


@dataclass(frozen=True, slots=True)
class ToolSchema:
    name: str
    description: str
    permission: ActionKind
    arguments: tuple[ToolArgument, ...] = ()

    def json_schema(self) -> dict[str, JsonValue]:  # noqa: DICT_OK
        properties = {
            item.name: {"type": item.schema_type.value, "description": item.name}
            for item in self.arguments
        }
        required = tuple(item.name for item in self.arguments if item.required)
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }


@dataclass(frozen=True, slots=True)
class ValidatedToolCall:
    id: str
    name: str
    arguments: dict[str, str]


class ToolValidationError(RuntimeError):
    pass


TOOLS: tuple[ToolSchema, ...] = (
    ToolSchema("filesystem.list", "List workspace files", ActionKind.READ_FILES),
    ToolSchema("filesystem.read", "Read a file inside the workspace", ActionKind.READ_FILES, (ToolArgument("path", SchemaType.STRING),)),
    ToolSchema(
        "filesystem.write",
        "Create or replace a file inside the workspace",
        ActionKind.WRITE_FILES,
        (ToolArgument("path", SchemaType.STRING), ToolArgument("content", SchemaType.STRING)),
    ),
    ToolSchema("workspace.search", "Search file names in the workspace", ActionKind.READ_FILES, (ToolArgument("term", SchemaType.STRING),)),
    ToolSchema("git.status", "Inspect Git status", ActionKind.READ_FILES),
    ToolSchema("git.diff", "Inspect Git diff summary", ActionKind.READ_FILES),
    ToolSchema("git.log", "Inspect recent Git commits", ActionKind.READ_FILES),
    ToolSchema("shell.run", "Run a safe shell command", ActionKind.SHELL, (ToolArgument("command", SchemaType.STRING),)),
    ToolSchema("http.get", "Read a URL over HTTP", ActionKind.NETWORK_READ, (ToolArgument("url", SchemaType.STRING),)),
)


def tool_schemas() -> tuple[ToolSchema, ...]:
    return TOOLS


def validate_tool_call(call: ToolCall) -> ValidatedToolCall:
    schema = _schema_for(call.name)
    values: dict[str, str] = {}
    allowed = {argument.name for argument in schema.arguments}
    for key in call.arguments:
        if key not in allowed:
            raise ToolValidationError(f'"{key}" is not a supported argument for {call.name}.')
    for argument in schema.arguments:
        value = call.arguments.get(argument.name)
        if value is None:
            if argument.required:
                raise ToolValidationError(f'"{argument.name}" is required.')
            continue
        match argument.schema_type:
            case SchemaType.STRING:
                if not isinstance(value, str):
                    raise ToolValidationError(f'"{argument.name}" must be a string.')
                values[argument.name] = value
            case unreachable:
                assert_never(unreachable)
    return ValidatedToolCall(call.id, call.name, values)


def execute_validated_tool(call: ValidatedToolCall, workspace: Path, interaction: Interaction | None) -> ToolResult:
    try:
        return _execute_validated_tool(call, workspace, interaction)
    except (PathSafetyError, ToolValidationError) as exc:
        return ToolResult(call.name, "tool rejected", tool_call_id=call.id, success=False, error=str(exc))


def _execute_validated_tool(call: ValidatedToolCall, workspace: Path, interaction: Interaction | None) -> ToolResult:
    match call.name:
        case "filesystem.list":
            return list_files(workspace).with_call(call.id)
        case "filesystem.read":
            return read_file(resolve_workspace_path(workspace, call.arguments["path"])).with_call(call.id)
        case "filesystem.write":
            path = resolve_workspace_path(workspace, call.arguments["path"])
            preview = preview_write(path, call.arguments["content"])
            request = PermissionRequest(ActionKind.WRITE_FILES, f"Create or modify {path.name}")
            if interaction is not None and interaction.approve(request, preview) is Approval.DENY:
                return ToolResult(call.name, "write denied", tool_call_id=call.id, success=False, error="Write denied")
            return write_file(path, call.arguments["content"]).with_call(call.id)
        case "workspace.search":
            return search_workspace(workspace, call.arguments["term"]).with_call(call.id)
        case "git.status":
            return git_status(workspace).with_call(call.id)
        case "git.diff":
            return git_diff(workspace).with_call(call.id)
        case "git.log":
            return git_log(workspace).with_call(call.id)
        case "shell.run":
            assessment = assess_shell_command(call.arguments["command"])
            if not assessment.safe:
                return ToolResult(call.name, "shell command rejected", tool_call_id=call.id, success=False, error=assessment.reason)
            request = PermissionRequest(ActionKind.SHELL, f"Run shell command: {call.arguments['command']}")
            if interaction is not None and interaction.approve(request) is Approval.DENY:
                return ToolResult(call.name, "shell denied", tool_call_id=call.id, success=False, error="Shell access denied")
            return shell_run(workspace, call.arguments["command"]).with_call(call.id)
        case "http.get":
            url = call.arguments["url"]
            host = urlparse(url).netloc
            if not host:
                raise ToolValidationError('"url" must include a host.')
            if interaction is not None and interaction.approve_network("GET", url, host) is Approval.DENY:
                return ToolResult(call.name, "network denied", tool_call_id=call.id, success=False, error="Network access denied")
            return http_get(url).with_call(call.id)
        case unreachable:
            assert_never(unreachable)


def _schema_for(name: str) -> ToolSchema:
    for schema in TOOLS:
        if schema.name == name:
            return schema
    raise ToolValidationError(f"Unknown tool: {name}")
