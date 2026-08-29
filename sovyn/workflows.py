from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum, unique
from pathlib import Path
import re

import yaml


@unique
class StepKind(StrEnum):
    DETERMINISTIC = "deterministic"
    PARAMETERIZED = "parameterized"
    MODEL_REQUIRED = "model-required"
    AGENT_REQUIRED = "agent-required"
    USER_REQUIRED = "user-required"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    tool: str
    kind: StepKind
    summary: str
    argument: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class Workflow:
    name: str
    description: str
    steps: tuple[WorkflowStep, ...]
    version: int = 1
    inputs: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    network: bool = False
    model_required: bool = False
    validation: tuple[str, ...] = ()
    project_types: tuple[str, ...] = ()
    required_binaries: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    intents: tuple[str, ...] = ()
    family: str = ""
    parent_version: int | None = None
    success_count: int = 0
    failure_count: int = 0
    evolution_reason: str = ""
    origin: str = "learned_local"
    created_at: str = ""


class WorkflowNameError(RuntimeError):
    pass


WINDOWS_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def workflow_path(directory: Path, name: str) -> Path:
    clean = _validated_workflow_name(name)
    root = directory.resolve()
    path = (root / f"{clean}.yaml").resolve()
    if path.parent != root:
        raise WorkflowNameError("Workflow name must stay inside the workflows directory")
    return path


def save_workflow(path: Path, workflow: Workflow) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": workflow.name,
        "description": workflow.description,
        "version": workflow.version,
        "inputs": list(workflow.inputs),
        "permissions": list(workflow.permissions),
        "network": workflow.network,
        "model_required": workflow.model_required,
        "validation": list(workflow.validation),
        "project_types": list(workflow.project_types),
        "required_binaries": list(workflow.required_binaries),
        "tags": list(workflow.tags),
        "intents": list(workflow.intents),
        "family": workflow.family or workflow.name,
        "parent_version": workflow.parent_version,
        "success_count": workflow.success_count,
        "failure_count": workflow.failure_count,
        "evolution_reason": workflow.evolution_reason,
        "origin": workflow.origin,
        "created_at": workflow.created_at or datetime.now(UTC).isoformat(),
        "trigger": {"manual": True},
        "steps": [
            {
                "tool": step.tool,
                "kind": step.kind.value,
                "summary": step.summary,
                "argument": step.argument,
                "content": step.content,
            }
            for step in workflow.steps
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _validated_workflow_name(name: str) -> str:
    clean = name.strip()
    if clean in {"", ".", ".."}:
        raise WorkflowNameError("Workflow name cannot be empty or reserved")
    candidate = Path(clean)
    if candidate.is_absolute() or len(candidate.parts) != 1:
        raise WorkflowNameError("Workflow name cannot include a path")
    if WINDOWS_INVALID_NAME.search(clean) is not None:
        raise WorkflowNameError("Workflow name contains invalid filename characters")
    return clean


def load_workflow(path: Path) -> Workflow:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Workflow(
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        steps=tuple(
            WorkflowStep(
                tool=str(step["tool"]),
                kind=StepKind(step["kind"]),
                summary=str(step.get("summary", "")),
                argument=str(step.get("argument", "")),
                content=str(step.get("content", "")),
            )
            for step in raw.get("steps", ())
        ),
        version=int(raw.get("version", 1)),
        inputs=tuple(str(item) for item in raw.get("inputs", ())),
        permissions=tuple(str(item) for item in raw.get("permissions", ())),
        network=bool(raw.get("network", False)),
        model_required=bool(raw.get("model_required", False)),
        validation=tuple(str(item) for item in raw.get("validation", ())),
        project_types=tuple(str(item) for item in raw.get("project_types", ())),
        required_binaries=tuple(str(item) for item in raw.get("required_binaries", ())),
        tags=tuple(str(item) for item in raw.get("tags", ())),
        intents=tuple(str(item) for item in raw.get("intents", ())),
        family=str(raw.get("family", raw["name"])),
        parent_version=int(raw["parent_version"]) if raw.get("parent_version") is not None else None,
        success_count=int(raw.get("success_count", 0)),
        failure_count=int(raw.get("failure_count", 0)),
        evolution_reason=str(raw.get("evolution_reason", "")),
        origin=str(raw.get("origin", "learned_local")),
        created_at=str(raw.get("created_at", "")),
    )


def list_workflows(directory: Path) -> tuple[Workflow, ...]:
    if not directory.exists():
        return ()
    return tuple(load_workflow(path) for path in sorted(directory.glob("*.yaml")))


def workflow_from_success(name: str, request: str, tools: tuple[str, ...]) -> Workflow:
    steps = tuple(WorkflowStep(tool=tool, kind=StepKind.DETERMINISTIC, summary=f"Reuse {tool}") for tool in tools)
    return Workflow(name=name, description=f"Reusable workflow for: {request}", steps=steps, model_required=False)


def workflow_from_steps(name: str, request: str, steps: tuple[WorkflowStep, ...]) -> Workflow:
    model_required = any(step.kind is StepKind.MODEL_REQUIRED or step.kind is StepKind.AGENT_REQUIRED for step in steps)
    return Workflow(name=name, description=f"Reusable workflow for: {request}", steps=steps, model_required=model_required)
