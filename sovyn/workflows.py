from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path

import yaml


@unique
class StepKind(StrEnum):
    DETERMINISTIC = "deterministic"
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


def save_workflow(path: Path, workflow: Workflow) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": workflow.name,
        "description": workflow.description,
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
    )


def list_workflows(directory: Path) -> tuple[Workflow, ...]:
    if not directory.exists():
        return ()
    return tuple(load_workflow(path) for path in sorted(directory.glob("*.yaml")))


def workflow_from_success(name: str, request: str, tools: tuple[str, ...]) -> Workflow:
    steps = tuple(WorkflowStep(tool=tool, kind=StepKind.DETERMINISTIC, summary=f"Reuse {tool}") for tool in tools)
    return Workflow(name=name, description=f"Reusable workflow for: {request}", steps=steps)


def workflow_from_steps(name: str, request: str, steps: tuple[WorkflowStep, ...]) -> Workflow:
    return Workflow(name=name, description=f"Reusable workflow for: {request}", steps=steps)
