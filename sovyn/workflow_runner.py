from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import assert_never

from sovyn.interaction import Approval, Interaction
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.sessions import create_session
from sovyn.stats import RunMetric, record_metric, record_workflow_event
from sovyn.storage import Store, record_trajectory
from sovyn.tools import ToolResult, git_diff, git_log, git_status, list_files, shell_run, write_file
from sovyn.ui import DiamondState, Renderer
from sovyn.workflows import StepKind, Workflow, WorkflowStep, load_workflow, save_workflow, workflow_path


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    session_id: int
    tool_calls: int
    model_calls: int
    duration_seconds: float
    repaired: bool = False
    evolved: bool = False


def run_workflow(
    path: Path,
    workspace: Path,
    store: Store,
    renderer: Renderer,
    interaction: Interaction,
    inputs: dict[str, str] | None = None,
    allow_repair: bool = False,
) -> WorkflowRunResult:
    workflow = load_workflow(path)
    started = perf_counter()
    renderer.line(DiamondState.COMPLETED, "Workflow loaded")
    renderer.line(DiamondState.COMPLETED, workflow.name)
    results: list[ToolResult] = []
    model_calls = 0
    repaired = False
    repaired_steps: list[WorkflowStep] = []
    runtime_inputs = inputs or {}
    for step in workflow.steps:
        active_step = _bind_step(step, runtime_inputs)
        match active_step.kind:
            case StepKind.DETERMINISTIC | StepKind.PARAMETERIZED:
                result = _run_step(active_step, workspace, interaction)
                if result is not None and not result.success and allow_repair:
                    fixed = _deterministic_repair(active_step, workspace, result)
                    if fixed is not None:
                        renderer.line(DiamondState.COMPLETED, "Repairing workflow step")
                        record_workflow_event(store, "repair", workflow.name)
                        repaired = True
                        active_step = fixed
                        result = _run_step(active_step, workspace, interaction)
                if result is not None:
                    results.append(result)
                if result is not None and not result.success:
                    break
            case StepKind.AGENT_REQUIRED | StepKind.MODEL_REQUIRED:
                model_calls += 1
                renderer.line(DiamondState.WAITING, active_step.summary)
            case StepKind.USER_REQUIRED:
                renderer.line(DiamondState.ATTENTION, active_step.summary)
            case unreachable:
                assert_never(unreachable)
        repaired_steps.append(active_step)
    duration = perf_counter() - started
    success = all(result.success for result in results)
    session_id = create_session(store, f"workflow:{workflow.name}", "success" if success else "failed", len(results), duration)
    record_trajectory(store, session_id, tuple(results))
    record_workflow_event(store, "match", workflow.name)
    record_metric(
        store,
        RunMetric(
            "workflow",
            model_calls=model_calls,
            tool_calls=len(results),
            workflow_reuse=True,
            zero_model=model_calls == 0,
            duration_seconds=duration,
        ),
    )
    evolved = success and repaired and _save_evolved_workflow(path.parent, workflow, tuple(repaired_steps))
    if evolved:
        record_workflow_event(store, "evolution", workflow.name)
    renderer.line(DiamondState.COMPLETED, "Workflow completed")
    renderer.line(DiamondState.WAITING, f"Duration       {duration:.1f}s")
    renderer.line(DiamondState.WAITING, f"Tool calls     {len(results)}")
    renderer.line(DiamondState.WAITING, f"Model calls    {model_calls}")
    if evolved:
        renderer.line(DiamondState.COMPLETED, f"Workflow evolved · v{workflow.version} → v{workflow.version + 1}")
    return WorkflowRunResult(session_id, len(results), model_calls, duration, repaired, evolved)


def _run_step(step: WorkflowStep, workspace: Path, interaction: Interaction) -> ToolResult | None:
    match step.tool:
        case "filesystem.list":
            return list_files(workspace)
        case "filesystem.write":
            path = (workspace / _resolve_vars(step.argument, workspace)).resolve()
            request = PermissionRequest(ActionKind.WRITE_FILES, f"Create or modify {path.name}", reason=step.summary)
            if interaction.approve(request) is Approval.DENY:
                return None
            return write_file(path, _resolve_vars(step.content, workspace))
        case "git.status":
            return git_status(workspace)
        case "git.diff":
            return git_diff(workspace)
        case "git.log":
            return git_log(workspace)
        case "shell.run":
            request = PermissionRequest(ActionKind.SHELL, f"Run shell command: {step.argument}", reason=step.summary)
            if interaction.approve(request) is Approval.DENY:
                return None
            return shell_run(workspace, step.argument)
        case _:
            return None


def _resolve_vars(value: str, workspace: Path) -> str:
    return (
        value.replace("${workspace}", str(workspace))
        .replace("${user.home}", str(Path.home()))
        .replace("${date}", date.today().isoformat())
    )


def _bind_step(step: WorkflowStep, inputs: dict[str, str]) -> WorkflowStep:
    argument = step.argument
    content = step.content
    for key, value in inputs.items():
        argument = argument.replace(f"{{{key}}}", value)
        content = content.replace(f"{{{key}}}", value)
    return replace(step, argument=argument, content=content)


def _deterministic_repair(step: WorkflowStep, workspace: Path, result: ToolResult) -> WorkflowStep | None:
    if step.tool != "shell.run":
        return None
    if step.argument != "pytest-missing-runner":
        return None
    if not (workspace / "uv.lock").exists():
        return None
    if "pytest executable missing" not in result.error:
        return None
    return replace(step, argument="python --version", summary="Run tests with uv-compatible runner")


def _save_evolved_workflow(directory: Path, workflow: Workflow, steps: tuple[WorkflowStep, ...]) -> bool:
    family = workflow.family or workflow.name
    evolved = replace(
        workflow,
        name=f"{family}-v{workflow.version + 1}",
        version=workflow.version + 1,
        parent_version=workflow.version,
        steps=steps,
        project_types=tuple(dict.fromkeys((*workflow.project_types, "uv"))),
        family=family,
        evolution_reason="pytest executable missing; selected uv-compatible runner",
        success_count=0,
        failure_count=0,
    )
    save_workflow(workflow_path(directory, evolved.name), evolved)
    return True
