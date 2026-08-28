from dataclasses import dataclass
from pathlib import Path
import re
from time import perf_counter

import anyio

from sovyn.diffing import preview_write
from sovyn.interaction import Approval, Interaction
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.providers import ModelProvider
from sovyn.sessions import create_session
from sovyn.storage import Store, record_trajectory
from sovyn.tools import ToolResult, git_diff, git_log, git_status, list_files, write_file
from sovyn.ui import DiamondState, Renderer
from sovyn.workflows import StepKind, Workflow, WorkflowStep, workflow_from_steps


@dataclass(frozen=True, slots=True)
class AgentResult:
    session_id: int
    response: str
    tools: tuple[ToolResult, ...]
    duration_seconds: float
    workflow: Workflow | None = None


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    provider: ModelProvider
    store: Store
    renderer: Renderer
    workspace: Path
    interaction: Interaction | None = None


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    argument: str = ""
    content: str = ""


def run_agent(request: str, runtime: AgentRuntime) -> AgentResult:
    started = perf_counter()
    if runtime.interaction is not None and not runtime.interaction.ensure_workspace_trusted(runtime.workspace):
        runtime.renderer.line(DiamondState.FAILED, "Workspace is not trusted")
        duration = perf_counter() - started
        session_id = create_session(runtime.store, request, "cancelled", 0, duration)
        return AgentResult(session_id=session_id, response="Operation cancelled.", tools=(), duration_seconds=duration)
    runtime.renderer.line(DiamondState.WAITING, "Reading workspace...")
    first = list_files(runtime.workspace)
    runtime.renderer.line(DiamondState.COMPLETED, first.summary)
    calls = _plan_calls(request)
    tools = _execute_calls(calls, runtime, (first,))
    runtime.renderer.line(DiamondState.WAITING, "Preparing response...")
    response = _stream_response(runtime.provider, _context_prompt(request, tools), runtime.renderer)
    duration = perf_counter() - started
    session_id = create_session(runtime.store, request, "success", len(tools), duration)
    record_trajectory(runtime.store, session_id, tools)
    runtime.renderer.line(DiamondState.COMPLETED, f"Task completed {duration:.1f}s")
    workflow = workflow_from_steps(_workflow_name(request), request, _workflow_steps(calls))
    return AgentResult(session_id=session_id, response=response, tools=tools, duration_seconds=duration, workflow=workflow)


def _execute_calls(calls: tuple[ToolCall, ...], runtime: AgentRuntime, initial: tuple[ToolResult, ...]) -> tuple[ToolResult, ...]:
    results = list(initial)
    for index, call in enumerate(calls, start=1):
        if index > 30:
            runtime.renderer.line(DiamondState.FAILED, "Step limit reached")
            break
        result = _execute_call(call, runtime)
        if result is not None:
            results.append(result)
    return tuple(results)


def _execute_call(call: ToolCall, runtime: AgentRuntime) -> ToolResult | None:
    match call.name:
        case "filesystem.write":
            path = (runtime.workspace / call.argument).resolve()
            preview = preview_write(path, call.content)
            request = PermissionRequest(ActionKind.WRITE_FILES, f"Create or modify {path.name}")
            if runtime.interaction is not None and runtime.interaction.approve(request, preview) is Approval.DENY:
                runtime.renderer.line(DiamondState.ATTENTION, "Write denied")
                return None
            runtime.renderer.line(DiamondState.WAITING, f"Writing {path.name}")
            result = write_file(path, call.content)
            runtime.renderer.line(DiamondState.COMPLETED, result.summary)
            return result
        case "git.status":
            runtime.renderer.line(DiamondState.WAITING, "Reading Git status...")
            result = git_status(runtime.workspace)
            runtime.renderer.line(DiamondState.COMPLETED, result.summary)
            return result
        case "git.diff":
            runtime.renderer.line(DiamondState.WAITING, "Reading Git diff...")
            result = git_diff(runtime.workspace)
            runtime.renderer.line(DiamondState.COMPLETED, result.summary)
            return result
        case "git.log":
            runtime.renderer.line(DiamondState.WAITING, "Reading Git history...")
            result = git_log(runtime.workspace)
            runtime.renderer.line(DiamondState.COMPLETED, result.summary)
            return result
        case _:
            return None


def _plan_calls(request: str) -> tuple[ToolCall, ...]:
    lowered = request.lower()
    file_match = re.search(r"create a file called ([^ ]+) containing (.+)", request, flags=re.IGNORECASE)
    if file_match is not None:
        return (ToolCall("filesystem.write", file_match.group(1), file_match.group(2)),)
    if "changed" in lowered or "status" in lowered:
        return (ToolCall("git.status"), ToolCall("git.diff"))
    if "commit" in lowered or "changelog" in lowered:
        return (ToolCall("git.log"),)
    return (ToolCall("git.status"),)


def _stream_response(provider: ModelProvider, prompt: str, renderer: Renderer) -> str:
    chunks = anyio.run(_collect_stream, provider, prompt)
    response = "".join(chunks)
    if response:
        renderer.stream_text(response)
    return response


async def _collect_stream(provider: ModelProvider, prompt: str) -> tuple[str, ...]:
    chunks: list[str] = []
    async for chunk in provider.stream(prompt):
        chunks.append(chunk)
    return tuple(chunks)


def _context_prompt(request: str, tools: tuple[ToolResult, ...]) -> str:
    observations = "\n".join(f"{tool.name}: {tool.summary}" for tool in tools)
    return f"User request: {request}\nTool observations:\n{observations}\nReturn a concise final answer."


def _workflow_name(request: str) -> str:
    words = tuple(re.findall(r"[a-z0-9]+", request.lower()))[:4]
    return "-".join(words) or "sovyn-workflow"


def _workflow_steps(calls: tuple[ToolCall, ...]) -> tuple[WorkflowStep, ...]:
    return tuple(
        WorkflowStep(call.name, StepKind.DETERMINISTIC, f"Run {call.name}", call.argument, call.content)
        for call in calls
    )
