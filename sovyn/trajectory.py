from dataclasses import dataclass
import re

from sovyn.permissions import ActionKind
from sovyn.tool_protocol import ToolCall
from sovyn.workflows import StepKind, Workflow, WorkflowStep


DETERMINISTIC_TOOLS = frozenset(("filesystem.list", "workspace.search", "git.status", "git.diff", "git.log", "shell.run"))
PARAMETERIZED_TOOLS = frozenset(("filesystem.read", "filesystem.write"))
MODEL_REQUIRED_TOOLS = frozenset(("http.get",))


@dataclass(frozen=True, slots=True)
class CompiledStep:
    step: WorkflowStep
    permission: str | None = None
    network: bool = False


def compile_trajectory(request: str, calls: tuple[ToolCall, ...]) -> Workflow:
    compiled = tuple(_compile_step(call) for call in calls)
    return Workflow(
        name=_workflow_name(request),
        description=f"Reusable workflow for: {request}",
        steps=tuple(item.step for item in compiled),
        version=1,
        inputs=_inputs_for(compiled),
        permissions=_permissions_for(compiled),
        network=any(item.network for item in compiled),
        model_required=any(item.step.kind is StepKind.MODEL_REQUIRED for item in compiled),
        validation=("replay exits successfully",),
    )


def _compile_step(call: ToolCall) -> CompiledStep:
    path = str(call.arguments.get("path", ""))
    content = str(call.arguments.get("content", ""))
    match _kind_for_tool(call.name):
        case StepKind.DETERMINISTIC:
            return CompiledStep(WorkflowStep(call.name, StepKind.DETERMINISTIC, f"Run {call.name}", path, content))
        case StepKind.PARAMETERIZED:
            permission = ActionKind.WRITE_FILES.value if call.name == "filesystem.write" else None
            return CompiledStep(WorkflowStep(call.name, StepKind.PARAMETERIZED, f"Run {call.name}", path, content), permission)
        case StepKind.MODEL_REQUIRED:
            return CompiledStep(WorkflowStep(call.name, StepKind.MODEL_REQUIRED, f"Resolve {call.name}", path, content), network=call.name == "http.get")
        case StepKind.AGENT_REQUIRED | StepKind.USER_REQUIRED:
            return CompiledStep(WorkflowStep(call.name, StepKind.MODEL_REQUIRED, f"Resolve {call.name}", path, content))


def _kind_for_tool(name: str) -> StepKind:
    if name in DETERMINISTIC_TOOLS:
        return StepKind.DETERMINISTIC
    if name in PARAMETERIZED_TOOLS:
        return StepKind.PARAMETERIZED
    if name in MODEL_REQUIRED_TOOLS:
        return StepKind.MODEL_REQUIRED
    return StepKind.MODEL_REQUIRED


def _inputs_for(steps: tuple[CompiledStep, ...]) -> tuple[str, ...]:
    values = []
    for item in steps:
        if item.step.argument:
            values.append(item.step.argument)
    return tuple(dict.fromkeys(values))


def _permissions_for(steps: tuple[CompiledStep, ...]) -> tuple[str, ...]:
    values = []
    for item in steps:
        if item.permission is not None:
            values.append(item.permission)
    return tuple(dict.fromkeys(values))


def _workflow_name(request: str) -> str:
    words = tuple(re.findall(r"[a-z0-9]+", request.lower()))[:4]
    return "-".join(words) or "sovyn-workflow"
