from dataclasses import dataclass
import json
from pathlib import Path
import re
from time import perf_counter

import anyio

from sovyn.agent_cache import CACHED_STALL_MESSAGE, CachedRepeatGuard, ToolCallCache
from sovyn.interaction import Interaction
from sovyn.loop_guard import LoopGuard
from sovyn.matcher import MatchDecision, WorkflowMatcher, WorkflowMatch
from sovyn.providers import ProviderError
from sovyn.providers import ModelProvider
from sovyn.references import reference_context
from sovyn.sessions import create_session
from sovyn.stats import RunMetric, record_metric
from sovyn.storage import Store, record_trajectory
from sovyn.config import DEFAULT_CONFIG
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tool_registry import ToolValidationError, execute_validated_tool, tool_schemas, validate_tool_call
from sovyn.tools import ToolResult, list_files
from sovyn.trajectory import compile_trajectory
from sovyn.ui import DiamondState, Renderer
from sovyn.undo import latest_undo_id, rename_undo_batches_after
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import Workflow


@dataclass(frozen=True, slots=True)
class AgentResult:
    session_id: int
    response: str
    tools: tuple[ToolResult, ...]
    duration_seconds: float
    workflow: Workflow | None = None
    model_calls: int = 0


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    provider: ModelProvider
    store: Store
    renderer: Renderer
    workspace: Path
    interaction: Interaction | None = None
    debug: bool = False
    workflows_dir: Path | None = None


def run_agent(request: str, runtime: AgentRuntime) -> AgentResult:
    started = perf_counter()
    if runtime.interaction is not None and not runtime.interaction.ensure_workspace_trusted(runtime.workspace):
        runtime.renderer.line(DiamondState.FAILED, "Workspace is not trusted")
        duration = perf_counter() - started
        session_id = create_session(runtime.store, request, "cancelled", 0, duration)
        return AgentResult(session_id=session_id, response="Operation cancelled.", tools=(), duration_seconds=duration)
    replay = _try_workflow_replay(request, runtime)
    if replay is not None:
        return replay
    runtime.renderer.line(DiamondState.WAITING, "Reading workspace...")
    first = list_files(runtime.workspace)
    runtime.renderer.line(DiamondState.COMPLETED, first.summary)
    undo_start = latest_undo_id(runtime.store)
    calls, tools, response, model_calls = _run_model_loop(request, runtime, first)
    runtime.renderer.line(DiamondState.WAITING, "Preparing response...")
    if response:
        runtime.renderer.stream_text(response)
    duration = perf_counter() - started
    if runtime.debug:
        runtime.renderer.line(DiamondState.COMPLETED, f"total             {duration:.2f}s")
    session_id = create_session(runtime.store, request, "success", len(tools), duration)
    record_trajectory(runtime.store, session_id, tools)
    rename_undo_batches_after(runtime.store, undo_start, request)
    record_metric(
        runtime.store,
        RunMetric("agent", model_calls=model_calls, tool_calls=len(tools), workflow_reuse=False, zero_model=False, duration_seconds=duration),
    )
    _render_completion(runtime.renderer, tools, duration)
    workflow = compile_trajectory(request, calls)
    if workflow.steps:
        runtime.renderer.line(DiamondState.COMPLETED, f"Reusable pattern detected · {workflow.name}")
    return AgentResult(session_id=session_id, response=response, tools=tools, duration_seconds=duration, workflow=workflow, model_calls=model_calls)


def _try_workflow_replay(request: str, runtime: AgentRuntime) -> AgentResult | None:
    if runtime.workflows_dir is None or runtime.interaction is None:
        return None
    match = WorkflowMatcher(runtime.workflows_dir).best_match(request, runtime.workspace)
    if runtime.debug and match.workflow.name:
        runtime.renderer.line(DiamondState.WAITING, f"workflow candidate {match.workflow.name} {match.confidence:.2f}")
    if match.decision is MatchDecision.SKIP:
        return None
    if match.decision is MatchDecision.ASK and not _confirm_match(runtime, match):
        return None
    runtime.renderer.line(DiamondState.COMPLETED, f"Reusing · {match.workflow.name}")
    result = run_workflow(
        runtime.workflows_dir / f"{match.workflow.name}.yaml",
        runtime.workspace,
        runtime.store,
        runtime.renderer,
        runtime.interaction,
        inputs=match.inputs,
        allow_repair=True,
    )
    return AgentResult(
        session_id=result.session_id,
        response="Workflow completed" if result.status == "success" else "Workflow failed",
        tools=(),
        duration_seconds=result.duration_seconds,
        workflow=match.workflow,
        model_calls=result.model_calls,
    )


def _confirm_match(runtime: AgentRuntime, match: WorkflowMatch) -> bool:
    if runtime.interaction is None or not runtime.interaction.interactive:
        return False
    runtime.renderer.line(DiamondState.ATTENTION, "Possible workflow found")
    runtime.renderer.line(DiamondState.WAITING, match.workflow.name)
    answer = runtime.interaction.prompter.ask("[y] use workflow  [n] normal agent: ").lower()
    return answer in {"y", "yes", ""}


def _run_model_loop(request: str, runtime: AgentRuntime, first: ToolResult) -> tuple[tuple[ToolCall, ...], tuple[ToolResult, ...], str, int]:
    results: list[ToolResult] = [first]
    calls: list[ToolCall] = []
    model_calls = 0
    guard = LoopGuard(limit=3)
    cache_guard = CachedRepeatGuard()
    cache = ToolCallCache()
    feedback = ""
    config = runtime.interaction.config if runtime.interaction is not None else DEFAULT_CONFIG
    for step in range(1, 1 + config.agent.max_steps):
        try:
            turn_started = perf_counter()
            turn = _model_turn(runtime.provider, _context_prompt(request, runtime.workspace, tuple(results), feedback), runtime.renderer)
            model_calls += 1
            if runtime.debug:
                runtime.renderer.line(DiamondState.WAITING, f"model turn {step:<2}      {perf_counter() - turn_started:.2f}s")
        except ProviderError as exc:
            runtime.renderer.line(DiamondState.FAILED, f"Provider unavailable: {exc.detail}")
            return tuple(calls), tuple(results), f"Provider unavailable: {exc.detail}", model_calls
        if not turn.tool_calls:
            return tuple(calls), tuple(results), turn.content, model_calls
        feedback = ""
        for call in turn.tool_calls:
            calls.append(call)
            cached = cache.result_for(call)
            if cached is None:
                cache_guard.reset()
                loop = guard.observe(call.name, json.dumps(call.arguments, sort_keys=True))
                if loop is not None:
                    runtime.renderer.line(DiamondState.ATTENTION, loop)
                    return tuple(calls), tuple(results), loop, model_calls
            result = _execute_tool_call(call, runtime, cache)
            results.append(result)
            if cached is not None:
                cached_repeat = cache_guard.observe(cache.repeat_key(call))
                if cached_repeat == CACHED_STALL_MESSAGE:
                    runtime.renderer.line(DiamondState.ATTENTION, cached_repeat)
                    return tuple(calls), tuple(results), cached_repeat, model_calls
                if cached_repeat is not None:
                    feedback = cached_repeat
            elif not result.success:
                feedback = _tool_rejection_feedback(result)
        if step == config.agent.max_steps:
            runtime.renderer.line(DiamondState.FAILED, "Step limit reached")
    return tuple(calls), tuple(results), "Step limit reached", model_calls


def _execute_tool_call(call: ToolCall, runtime: AgentRuntime, cache: ToolCallCache) -> ToolResult:
    try:
        validated = validate_tool_call(call)
    except ToolValidationError as exc:
        runtime.renderer.line(DiamondState.FAILED, "Tool call rejected")
        runtime.renderer.line(DiamondState.WAITING, call.name)
        runtime.renderer.line(DiamondState.WAITING, f"Reason: {exc}")
        return ToolResult(call.name, "tool rejected", tool_call_id=call.id, success=False, error=str(exc))
    cached = cache.result_for(call)
    if cached is not None:
        runtime.renderer.line(DiamondState.WAITING, f"Reusing {_semantic_action(validated.name)}")
        return cached.with_call(call.id)
    runtime.renderer.line(DiamondState.WAITING, _semantic_action(validated.name))
    tool_started = perf_counter()
    result = execute_validated_tool(validated, runtime.workspace, runtime.interaction)
    elapsed = perf_counter() - tool_started
    cache.store(call, result)
    cache.observe(result)
    state = DiamondState.COMPLETED if result.success else DiamondState.FAILED
    runtime.renderer.line(state, result.summary)
    if runtime.debug:
        runtime.renderer.line(DiamondState.WAITING, f"{validated.name:<18} {elapsed:.2f}s")
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


def _context_prompt(request: str, workspace: Path, tools: tuple[ToolResult, ...], feedback: str = "") -> str:
    observations = "\n".join(_tool_observation(tool) for tool in tools[-8:])
    tool_names = ", ".join(schema.name for schema in tool_schemas())
    references = reference_context(request, workspace)
    return (
        f"User request: {request}\n"
        f"{references}\n"
        f"Available tools: {tool_names}\n"
        f"Tool observations:\n{observations}\n"
        f"{feedback}\n"
        "Use native tool calls when available. In compatibility mode, emit exactly one <tool>{...}</tool> block. "
        "Do not repeat an identical successful tool call unless the workspace may have changed. "
        "Use existing tool observations whenever they already contain the needed information. "
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


def _semantic_action(name: str) -> str:
    actions = {
        "filesystem.list": "Inspecting project",
        "filesystem.read": "Reading file",
        "filesystem.write": "Updating file",
        "workspace.search": "Searching files",
        "git.status": "Reading Git status",
        "git.diff": "Reading Git diff",
        "git.log": "Reading Git history",
        "shell.run": "Running command",
        "http.get": "Reading URL",
    }
    return actions.get(name, name)


def _render_completion(renderer: Renderer, tools: tuple[ToolResult, ...], duration: float) -> None:
    changed = tuple(tool.output for tool in tools if tool.success and tool.name == "filesystem.write")
    verified = tuple(tool.summary for tool in tools if tool.success and tool.name == "shell.run" and tool.summary == "exit 0")
    renderer.line(DiamondState.COMPLETED, "Done")
    if changed:
        renderer.stream_text("Changed")
        for path in changed:
            renderer.stream_text(Path(path).name)
    if verified:
        renderer.stream_text("Verification")
        for item in verified:
            renderer.stream_text(item)
    renderer.stream_text("Time")
    renderer.stream_text(f"{duration:.1f}s")
