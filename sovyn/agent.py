import json
import re
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from time import perf_counter

import anyio

from sovyn.agent_cache import CACHED_STALL_MESSAGE, CachedRepeatGuard, ToolCallCache
from sovyn.assist.language import direct_identity_answer, identity_instruction, prepare_request
from sovyn.assist.recovery import exact_write_verified, parse_text_tool_call, recovery_attempt
from sovyn.config import DEFAULT_CONFIG, InterfaceLanguage
from sovyn.interaction import Interaction
from sovyn.loop_guard import LoopGuard
from sovyn.matcher import MatchDecision, WorkflowMatch, WorkflowMatcher
from sovyn.providers import ModelProvider, ProviderError
from sovyn.references import reference_context
from sovyn.sessions import create_session
from sovyn.stats import RunMetric, record_metric
from sovyn.storage import Store, record_trajectory
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tool_registry import ToolValidationError, execute_validated_tool, tool_schemas, validate_tool_call
from sovyn.tools import ToolResult, list_files
from sovyn.trajectory import compile_trajectory
from sovyn.ui import DiamondState, Renderer
from sovyn.undo import latest_undo_id, rename_undo_batches_after
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import Workflow


@unique
class RunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    STALLED = "stalled"
    CANCELLED = "cancelled"
    PROVIDER_ERROR = "provider_error"
    STEP_LIMIT = "step_limit"


@dataclass(frozen=True, slots=True)
class AgentResult:
    session_id: int
    response: str
    tools: tuple[ToolResult, ...]
    duration_seconds: float
    workflow: Workflow | None = None
    model_calls: int = 0
    status: RunStatus = RunStatus.SUCCESS


@dataclass(frozen=True, slots=True)
class ModelLoopResult:
    calls: tuple[ToolCall, ...]
    tools: tuple[ToolResult, ...]
    response: str
    model_calls: int
    status: RunStatus


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
    config = runtime.interaction.config if runtime.interaction is not None else DEFAULT_CONFIG
    prepared = prepare_request(request, config, runtime.provider.name)
    direct = direct_identity_answer(request, prepared.language, runtime.provider.name)
    if direct is not None:
        duration = perf_counter() - started
        session_id = create_session(runtime.store, request, RunStatus.SUCCESS.value, 0, duration)
        runtime.renderer.stream_text(direct)
        _render_completion(runtime.renderer, RunStatus.SUCCESS, (), duration)
        return AgentResult(session_id, direct, (), duration, model_calls=0, status=RunStatus.SUCCESS)
    if runtime.interaction is not None and not runtime.interaction.ensure_workspace_trusted(runtime.workspace):
        runtime.renderer.line(DiamondState.FAILED, "Workspace is not trusted")
        duration = perf_counter() - started
        session_id = create_session(runtime.store, request, RunStatus.CANCELLED.value, 0, duration)
        return AgentResult(
            session_id=session_id,
            response="Operation cancelled.",
            tools=(),
            duration_seconds=duration,
            status=RunStatus.CANCELLED,
        )
    replay = _try_workflow_replay(request, runtime)
    if replay is not None:
        return replay
    runtime.renderer.line(DiamondState.WAITING, "Reading workspace...")
    first = list_files(runtime.workspace)
    runtime.renderer.line(DiamondState.COMPLETED, first.summary)
    undo_start = latest_undo_id(runtime.store)
    loop_result = _run_model_loop(request, prepared.prompt, runtime, first)
    calls = loop_result.calls
    tools = loop_result.tools
    response = loop_result.response
    model_calls = loop_result.model_calls
    status = _verified_status(request, loop_result)
    runtime.renderer.line(DiamondState.WAITING, "Preparing response...")
    if response:
        runtime.renderer.stream_text(response)
    duration = perf_counter() - started
    if runtime.debug:
        runtime.renderer.line(DiamondState.COMPLETED, f"total             {duration:.2f}s")
    session_id = create_session(runtime.store, request, status.value, len(tools), duration)
    record_trajectory(runtime.store, session_id, tools)
    if status is RunStatus.SUCCESS:
        rename_undo_batches_after(runtime.store, undo_start, request)
    record_metric(
        runtime.store,
        RunMetric(
            "agent",
            model_calls=model_calls,
            tool_calls=len(tools),
            workflow_reuse=False,
            zero_model=False,
            duration_seconds=duration,
        ),
    )
    _render_completion(runtime.renderer, status, tools, duration)
    workflow = compile_trajectory(request, calls) if _workflow_allowed(status, tools) else None
    if workflow is not None and workflow.steps:
        runtime.renderer.line(DiamondState.COMPLETED, f"Reusable pattern detected · {workflow.name}")
    return AgentResult(
        session_id=session_id,
        response=response,
        tools=tools,
        duration_seconds=duration,
        workflow=workflow,
        model_calls=model_calls,
        status=status,
    )


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
        status=RunStatus.SUCCESS if result.status == "success" else RunStatus.FAILED,
    )


def _confirm_match(runtime: AgentRuntime, match: WorkflowMatch) -> bool:
    if runtime.interaction is None or not runtime.interaction.interactive:
        return False
    runtime.renderer.line(DiamondState.ATTENTION, "Possible workflow found")
    runtime.renderer.line(DiamondState.WAITING, match.workflow.name)
    answer = runtime.interaction.prompter.ask("[y] use workflow  [n] normal agent: ").lower()
    return answer in {"y", "yes", ""}


def _run_model_loop(original_request: str, request: str, runtime: AgentRuntime, first: ToolResult) -> ModelLoopResult:
    results: list[ToolResult] = [first]
    calls: list[ToolCall] = []
    model_calls = 0
    guard = LoopGuard(limit=3)
    cache_guard = CachedRepeatGuard()
    cache = ToolCallCache()
    feedback = ""
    config = runtime.interaction.config if runtime.interaction is not None else DEFAULT_CONFIG
    prepared = prepare_request(original_request, config, runtime.provider.name)
    recovery_used = False
    for step in range(1, 1 + config.agent.max_steps):
        try:
            turn_started = perf_counter()
            turn = _model_turn(
                runtime.provider,
                _context_prompt(
                    request,
                    runtime.workspace,
                    tuple(results),
                    prepared.language,
                    runtime.provider.name,
                    feedback,
                ),
                runtime.renderer,
            )
            model_calls += 1
            if runtime.debug:
                runtime.renderer.line(
                    DiamondState.WAITING, f"model turn {step:<2}      {perf_counter() - turn_started:.2f}s"
                )
        except ProviderError as exc:
            runtime.renderer.line(DiamondState.FAILED, f"Provider unavailable: {exc.detail}")
            return ModelLoopResult(
                tuple(calls),
                tuple(results),
                f"Provider unavailable: {exc.detail}",
                model_calls,
                RunStatus.PROVIDER_ERROR,
            )
        if not turn.tool_calls:
            repaired_calls = parse_text_tool_call(turn.content) if config.assist.enabled else ()
            if repaired_calls:
                turn = ProviderTurn("", repaired_calls, turn.usage)
            else:
                return ModelLoopResult(tuple(calls), tuple(results), turn.content, model_calls, RunStatus.SUCCESS)
        feedback = ""
        for call in turn.tool_calls:
            calls.append(call)
            cached = cache.result_for(call)
            if cached is None:
                cache_guard.reset()
                loop = guard.observe(call.name, json.dumps(call.arguments, sort_keys=True))
                if loop is not None:
                    verified = exact_write_verified(original_request, runtime.workspace, tuple(results))
                    if verified is not None:
                        return ModelLoopResult(tuple(calls), tuple(results), verified, model_calls, RunStatus.SUCCESS)
                    if not recovery_used:
                        recovered = _recover_final(
                            original_request,
                            runtime,
                            tuple(results),
                            prepared.language,
                            loop,
                        )
                        recovery_used = True
                        if recovered is not None:
                            return _with_model_calls(recovered, model_calls + 1)
                    runtime.renderer.line(DiamondState.ATTENTION, loop)
                    return ModelLoopResult(tuple(calls), tuple(results), loop, model_calls, RunStatus.STALLED)
            result = _execute_tool_call(call, runtime, cache)
            results.append(result)
            if cached is not None:
                cached_repeat = cache_guard.observe(cache.repeat_key(call))
                if cached_repeat == CACHED_STALL_MESSAGE:
                    verified = exact_write_verified(original_request, runtime.workspace, tuple(results))
                    if verified is not None:
                        return ModelLoopResult(tuple(calls), tuple(results), verified, model_calls, RunStatus.SUCCESS)
                    if not recovery_used:
                        recovered = _recover_final(
                            original_request,
                            runtime,
                            tuple(results),
                            prepared.language,
                            cached_repeat,
                        )
                        recovery_used = True
                        if recovered is not None:
                            return _with_model_calls(recovered, model_calls + 1)
                    runtime.renderer.line(DiamondState.ATTENTION, cached_repeat)
                    return ModelLoopResult(tuple(calls), tuple(results), cached_repeat, model_calls, RunStatus.STALLED)
                if cached_repeat is not None:
                    feedback = cached_repeat
            elif not result.success:
                feedback = _tool_rejection_feedback(result)
        if step == config.agent.max_steps:
            runtime.renderer.line(DiamondState.FAILED, "Step limit reached")
    return ModelLoopResult(tuple(calls), tuple(results), "Step limit reached", model_calls, RunStatus.STEP_LIMIT)


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


def _recover_final(
    request: str,
    runtime: AgentRuntime,
    tools: tuple[ToolResult, ...],
    language: InterfaceLanguage,
    reason: str,
) -> ModelLoopResult | None:
    attempt = recovery_attempt(request, tools, language, reason)
    if attempt is None:
        return None
    try:
        response = anyio.run(runtime.provider.generate, attempt.prompt).strip()
    except ProviderError:
        return None
    if response == "":
        return None
    runtime.renderer.line(DiamondState.ATTENTION, f"Recovery turn: {attempt.reason}")
    return ModelLoopResult((), tools, response, 0, RunStatus.SUCCESS)


def _with_model_calls(result: ModelLoopResult, model_calls: int) -> ModelLoopResult:
    return ModelLoopResult(result.calls, result.tools, result.response, model_calls, result.status)


async def _collect_stream(provider: ModelProvider, prompt: str) -> tuple[str, ...]:
    chunks: list[str] = []
    async for chunk in provider.stream(prompt):
        chunks.append(chunk)
    return tuple(chunks)


def _context_prompt(
    request: str,
    workspace: Path,
    tools: tuple[ToolResult, ...],
    language: InterfaceLanguage,
    model_name: str = "",
    feedback: str = "",
) -> str:
    observations = "\n".join(_tool_observation(tool) for tool in tools[-8:])
    tool_names = ", ".join(schema.name for schema in tool_schemas())
    references = reference_context(request, workspace)
    return (
        f"User request: {request}\n"
        f"{identity_instruction(language, model_name or 'configured model')}\n"
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
    return (
        f"Tool execution failed.\n{result.name}\n"
        f"Reason:\n{result.error}\n"
        "Do not claim the task succeeded unless the failure is resolved."
    )


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


def _verified_status(request: str, loop_result: ModelLoopResult) -> RunStatus:
    if loop_result.status is not RunStatus.SUCCESS:
        return loop_result.status
    if any(not tool.success for tool in loop_result.tools):
        return RunStatus.FAILED
    if _requires_action(request) and not _has_action_evidence(loop_result.tools):
        return RunStatus.FAILED
    return RunStatus.SUCCESS


def _requires_action(request: str) -> bool:
    return (
        re.search(
            r"(create|write|change|modify|update|delete|remove|run|execute|check|fix|make|move|rename|작성|생성|만들|수정|변경|삭제|실행|확인)",
            request.lower(),
        )
        is not None
    )


def _has_action_evidence(tools: tuple[ToolResult, ...]) -> bool:
    return any(
        tool.success
        and tool.name
        in {
            "filesystem.write",
            "filesystem.move",
            "filesystem.delete",
            "shell.run",
            "git.status",
            "git.diff",
            "git.log",
        }
        for tool in tools
    )


def _workflow_allowed(status: RunStatus, tools: tuple[ToolResult, ...]) -> bool:
    if status is not RunStatus.SUCCESS:
        return False
    return all(tool.success for tool in tools)


def _render_completion(renderer: Renderer, status: RunStatus, tools: tuple[ToolResult, ...], duration: float) -> None:
    changed = tuple(
        dict.fromkeys(
            tool.output for tool in tools if tool.success and tool.name == "filesystem.write" and not tool.no_change
        )
    )
    verified = tuple(
        tool.summary for tool in tools if tool.success and tool.name == "shell.run" and tool.summary == "exit 0"
    )
    match status:
        case RunStatus.SUCCESS:
            renderer.line(DiamondState.COMPLETED, "Done")
        case RunStatus.STALLED:
            renderer.line(DiamondState.ATTENTION, "Stalled")
        case RunStatus.PROVIDER_ERROR:
            renderer.line(DiamondState.FAILED, "Provider unavailable")
        case RunStatus.FAILED | RunStatus.CANCELLED | RunStatus.STEP_LIMIT:
            renderer.line(DiamondState.FAILED, "Failed")
        case unreachable:
            raise AssertionError(f"unknown run status: {unreachable}")
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
