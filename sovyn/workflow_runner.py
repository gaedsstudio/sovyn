from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter

from sovyn.interaction import Approval, Interaction
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.sessions import create_session
from sovyn.storage import Store, record_trajectory
from sovyn.tools import ToolResult, git_diff, git_log, git_status, list_files, write_file
from sovyn.ui import DiamondState, Renderer
from sovyn.workflows import StepKind, Workflow, WorkflowStep, load_workflow


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    session_id: int
    tool_calls: int
    model_calls: int
    duration_seconds: float


def run_workflow(path: Path, workspace: Path, store: Store, renderer: Renderer, interaction: Interaction) -> WorkflowRunResult:
    workflow = load_workflow(path)
    started = perf_counter()
    renderer.line(DiamondState.COMPLETED, "Workflow loaded")
    renderer.line(DiamondState.COMPLETED, workflow.name)
    results: list[ToolResult] = []
    model_calls = 0
    for step in workflow.steps:
        match step.kind:
            case StepKind.DETERMINISTIC:
                result = _run_step(step, workspace, interaction)
                if result is not None:
                    results.append(result)
            case StepKind.AGENT_REQUIRED:
                model_calls += 1
                renderer.line(DiamondState.WAITING, step.summary)
            case StepKind.USER_REQUIRED:
                renderer.line(DiamondState.ATTENTION, step.summary)
    duration = perf_counter() - started
    session_id = create_session(store, f"workflow:{workflow.name}", "success", len(results), duration)
    record_trajectory(store, session_id, tuple(results))
    renderer.line(DiamondState.COMPLETED, "Workflow completed")
    renderer.line(DiamondState.WAITING, f"Duration       {duration:.1f}s")
    renderer.line(DiamondState.WAITING, f"Tool calls     {len(results)}")
    renderer.line(DiamondState.WAITING, f"Model calls    {model_calls}")
    return WorkflowRunResult(session_id, len(results), model_calls, duration)


def _run_step(step: WorkflowStep, workspace: Path, interaction: Interaction) -> ToolResult | None:
    match step.tool:
        case "filesystem.list":
            return list_files(workspace)
        case "filesystem.write":
            path = (workspace / _resolve_vars(step.argument, workspace)).resolve()
            request = PermissionRequest(ActionKind.WRITE_FILES, f"Create or modify {path.name}")
            if interaction.approve(request) is Approval.DENY:
                return None
            return write_file(path, _resolve_vars(step.content, workspace))
        case "git.status":
            return git_status(workspace)
        case "git.diff":
            return git_diff(workspace)
        case "git.log":
            return git_log(workspace)
        case _:
            return None


def _resolve_vars(value: str, workspace: Path) -> str:
    return (
        value.replace("${workspace}", str(workspace))
        .replace("${user.home}", str(Path.home()))
        .replace("${date}", date.today().isoformat())
    )
