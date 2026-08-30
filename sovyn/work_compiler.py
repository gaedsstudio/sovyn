import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Final

from sovyn.path_safety import PathSafetyError, resolve_workspace_path
from sovyn.permissions import ActionKind
from sovyn.tool_protocol import JsonValue, ToolCall
from sovyn.tools import ToolResult
from sovyn.workflows import StepKind, Workflow, WorkflowStep

DETERMINISTIC_TOOLS: Final = frozenset(
    ("filesystem.list", "filesystem.read", "workspace.search", "git.status", "git.diff", "git.log", "shell.run")
)
WRITE_TOOLS: Final = frozenset(("filesystem.write",))
MODEL_REQUIRED_TOOLS: Final = frozenset(("http.get",))
SEMANTIC_TRIGGERS: Final = frozenset(
    (
        "summarize",
        "explain",
        "refactor",
        "research",
        "decide",
        "rewrite",
        "improve",
        "analyze",
        "요약",
        "설명",
        "분석",
        "리팩터",
    )
)


@dataclass(frozen=True, slots=True)
class SuccessfulRun:
    request: str
    calls: tuple[ToolCall, ...]
    results: tuple[ToolResult, ...]
    workspace: Path


@dataclass(frozen=True, slots=True)
class CompileResult:
    workflow: Workflow | None
    deterministic: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PairedExecution:
    call: ToolCall
    result: ToolResult


@dataclass(frozen=True, slots=True)
class CompiledExecution:
    step: WorkflowStep
    permission: str | None = None
    network: bool = False
    model_required: bool = False


def compile_successful_run(run: SuccessfulRun) -> CompileResult:
    pairs = _pair_calls_and_results(run.calls, run.results)
    if any(not pair.result.success for pair in pairs):
        return CompileResult(None, False, ("failed tool result",))
    compiled: list[CompiledExecution] = []
    reasons: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for pair in pairs:
        item = _compile_pair(pair, run.workspace)
        if item is None:
            reasons.append(f"unsupported {pair.call.name}")
            continue
        key = (item.step.tool, item.step.argument, item.step.content)
        if key in seen:
            reasons.append(f"collapsed duplicate {item.step.tool}")
            continue
        seen.add(key)
        compiled.append(item)
    if not compiled:
        return CompileResult(None, False, tuple(reasons or ("no meaningful successful steps",)))
    model_required = _requires_model(run.request) or any(item.model_required for item in compiled)
    workflow = Workflow(
        name=_workflow_name(run.request),
        description=f"Reusable workflow for: {run.request}",
        steps=tuple(item.step for item in compiled),
        inputs=(),
        permissions=_permissions_for(tuple(compiled)),
        network=any(item.network for item in compiled),
        model_required=model_required,
        validation=("all deterministic steps must succeed",),
    )
    return CompileResult(workflow, not model_required, tuple(reasons))


def _pair_calls_and_results(
    calls: tuple[ToolCall, ...], results: tuple[ToolResult, ...]
) -> tuple[PairedExecution, ...]:
    remaining = list(calls)
    paired: list[PairedExecution] = []
    for result in results:
        match_index = _matching_call_index(remaining, result)
        if match_index is None:
            continue
        call = remaining.pop(match_index)
        paired.append(PairedExecution(call, result))
    return tuple(paired)


def _matching_call_index(calls: list[ToolCall], result: ToolResult) -> int | None:
    for index, call in enumerate(calls):
        if call.name == result.name and (result.tool_call_id == "" or call.id == result.tool_call_id):
            return index
    return None


def _compile_pair(pair: PairedExecution, workspace: Path) -> CompiledExecution | None:
    path = _path_argument(pair.call.arguments, workspace)
    content = _string_argument(pair.call.arguments, "content")
    match pair.call.name:
        case "filesystem.list" | "git.status" | "git.diff" | "git.log":
            return CompiledExecution(WorkflowStep(pair.call.name, StepKind.DETERMINISTIC, f"Run {pair.call.name}"))
        case "filesystem.read":
            if path is None:
                return None
            return CompiledExecution(
                WorkflowStep(pair.call.name, StepKind.DETERMINISTIC, f"Run {pair.call.name}", path)
            )
        case "filesystem.write":
            if path is None:
                return None
            return CompiledExecution(
                WorkflowStep(pair.call.name, StepKind.DETERMINISTIC, f"Run {pair.call.name}", path, content),
                ActionKind.WRITE_FILES.value,
            )
        case "workspace.search":
            return CompiledExecution(
                WorkflowStep(
                    pair.call.name,
                    StepKind.DETERMINISTIC,
                    f"Run {pair.call.name}",
                    _string_argument(pair.call.arguments, "term"),
                )
            )
        case "shell.run":
            return CompiledExecution(
                WorkflowStep(
                    pair.call.name,
                    StepKind.DETERMINISTIC,
                    f"Run {pair.call.name}",
                    _string_argument(pair.call.arguments, "command"),
                ),
                ActionKind.SHELL.value,
            )
        case "http.get":
            return CompiledExecution(
                WorkflowStep(
                    pair.call.name,
                    StepKind.MODEL_REQUIRED,
                    f"Resolve {pair.call.name}",
                    _string_argument(pair.call.arguments, "url"),
                ),
                ActionKind.NETWORK_READ.value,
                network=True,
                model_required=True,
            )
        case _:
            return None


def _path_argument(arguments: Mapping[str, JsonValue], workspace: Path) -> str | None:
    raw = _string_argument(arguments, "path")
    if raw == "":
        return None
    try:
        resolved = resolve_workspace_path(workspace, raw)
    except PathSafetyError:
        return None
    try:
        return str(resolved.relative_to(workspace.resolve()))
    except ValueError:
        return str(resolved)


def _string_argument(arguments: Mapping[str, JsonValue], name: str) -> str:
    value = arguments.get(name, "")
    return value if isinstance(value, str) else ""


def _permissions_for(items: tuple[CompiledExecution, ...]) -> tuple[str, ...]:
    values = tuple(item.permission for item in items if item.permission is not None)
    return tuple(dict.fromkeys(values))


def _requires_model(request: str) -> bool:
    normalized = request.lower()
    return any(trigger in normalized for trigger in SEMANTIC_TRIGGERS)


def _workflow_name(request: str) -> str:
    words = tuple(re.findall(r"[a-z0-9]+", request.lower()))[:4]
    if words:
        return "-".join(words)
    return f"workflow-{sha256(request.encode('utf-8')).hexdigest()[:8]}"
