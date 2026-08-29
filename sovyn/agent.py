from dataclasses import dataclass
import json
from pathlib import Path
import re
from time import perf_counter

import anyio

from sovyn.interaction import Interaction
from sovyn.loop_guard import LoopGuard
from sovyn.providers import ProviderError
from sovyn.providers import ModelProvider
from sovyn.sessions import create_session
from sovyn.storage import Store, record_trajectory
from sovyn.config import DEFAULT_CONFIG
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tool_registry import ToolValidationError, execute_validated_tool, tool_schemas, validate_tool_call
from sovyn.tools import ToolResult, list_files
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
    calls, tools, response = _run_model_loop(request, runtime, first)
    runtime.renderer.line(DiamondState.WAITING, "Preparing response...")
    if response:
        runtime.renderer.stream_text(response)
    duration = perf_counter() - started
    session_id = create_session(runtime.store, request, "success", len(tools), duration)
    record_trajectory(runtime.store, session_id, tools)
    runtime.renderer.line(DiamondState.COMPLETED, f"Task completed {duration:.1f}s")
    workflow = workflow_from_steps(_workflow_name(request), request, _workflow_steps(calls))
    return AgentResult(session_id=session_id, response=response, tools=tools, duration_seconds=duration, workflow=workflow)


def _run_model_loop(request: str, runtime: AgentRuntime, first: ToolResult) -> tuple[tuple[ToolCall, ...], tuple[ToolResult, ...], str]:
    results: list[ToolResult] = [first]
    calls: list[ToolCall] = []
    guard = LoopGuard(limit=3)
    feedback = ""
    config = runtime.interaction.config if runtime.interaction is not None else DEFAULT_CONFIG
    for step in range(1, 1 + config.agent.max_steps):
        try:
            turn = _model_turn(runtime.provider, _context_prompt(request, tuple(results), feedback), runtime.renderer)
        except ProviderError as exc:
            runtime.renderer.line(DiamondState.FAILED, f"Provider unavailable: {exc.detail}")
            return tuple(calls), tuple(results), f"Provider unavailable: {exc.detail}"
        if not turn.tool_calls:
            return tuple(calls), tuple(results), turn.content
        feedback = ""
        for call in turn.tool_calls:
            calls.append(call)
            loop = guard.observe(call.name, json.dumps(call.arguments, sort_keys=True))
            if loop is not None:
                runtime.renderer.line(DiamondState.ATTENTION, loop)
                return tuple(calls), tuple(results), loop
            result = _execute_tool_call(call, runtime)
            results.append(result)
            if not result.success:
                feedback = _tool_rejection_feedback(result)
        if step == config.agent.max_steps:
            runtime.renderer.line(DiamondState.FAILED, "Step limit reached")
    return tuple(calls), tuple(results), "Step limit reached"


def _execute_tool_call(call: ToolCall, runtime: AgentRuntime) -> ToolResult:
    try:
        validated = validate_tool_call(call)
    except ToolValidationError as exc:
        runtime.renderer.line(DiamondState.FAILED, "Tool call rejected")
        runtime.renderer.line(DiamondState.WAITING, call.name)
        runtime.renderer.line(DiamondState.WAITING, f"Reason: {exc}")
        return ToolResult(call.name, "tool rejected", tool_call_id=call.id, success=False, error=str(exc))
    runtime.renderer.line(DiamondState.WAITING, f"Running {validated.name}")
    result = execute_validated_tool(validated, runtime.workspace, runtime.interaction)
    state = DiamondState.COMPLETED if result.success else DiamondState.FAILED
    runtime.renderer.line(state, result.summary)
    return result


def _model_turn(provider: ModelProvider, prompt: str, renderer: Renderer) -> ProviderTurn:
    turn = anyio.run(provider.turn, prompt, tool_schemas())
    if turn.content and not turn.tool_calls:
        return turn
    if turn.tool_calls:
        return turn
    chunks = anyio.run(_collect_stream, provider, prompt)
    return ProviderTurn("".join(chunks))


async def _collect_stream(provider: ModelProvider, prompt: str) -> tuple[str, ...]:
    chunks: list[str] = []
    async for chunk in provider.stream(prompt):
        chunks.append(chunk)
    return tuple(chunks)


def _context_prompt(request: str, tools: tuple[ToolResult, ...], feedback: str = "") -> str:
    observations = "\n".join(_tool_observation(tool) for tool in tools[-8:])
    tool_names = ", ".join(schema.name for schema in tool_schemas())
    return (
        f"User request: {request}\n"
        f"Available tools: {tool_names}\n"
        f"Tool observations:\n{observations}\n"
        f"{feedback}\n"
        "Use native tool calls when available. In compatibility mode, emit exactly one <tool>{...}</tool> block. "
        "Return a concise final answer when the task is complete."
    )


def _tool_observation(tool: ToolResult) -> str:
    output = tool.output[:400]
    suffix = " [truncated]" if len(tool.output) > 400 else ""
    return f"{tool.name}: {tool.summary} {output}{suffix}".strip()


def _tool_rejection_feedback(result: ToolResult) -> str:
    return f"Tool call rejected\n{result.name}\nReason:\n{result.error}\nCorrect the arguments or stop."


def _workflow_name(request: str) -> str:
    words = tuple(re.findall(r"[a-z0-9]+", request.lower()))[:4]
    return "-".join(words) or "sovyn-workflow"


def _workflow_steps(calls: tuple[ToolCall, ...]) -> tuple[WorkflowStep, ...]:
    return tuple(
        WorkflowStep(call.name, StepKind.DETERMINISTIC, f"Run {call.name}", str(call.arguments.get("path", "")), str(call.arguments.get("content", "")))
        for call in calls
    )
