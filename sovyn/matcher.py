from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
import re
from time import perf_counter

from sovyn.references import ReferenceKind, parse_references
from sovyn.workflows import Workflow, WorkflowStep, list_workflows


RUN_THRESHOLD = 0.72
ASK_THRESHOLD = 0.45
DESTRUCTIVE_TOOLS = frozenset(("filesystem.delete", "git.clean", "git.checkout"))
STOPWORDS = frozenset(("a", "an", "again", "do", "please", "the", "this"))
SYNONYMS = {
    "broke": "repair",
    "broken": "repair",
    "fix": "repair",
    "failure": "repair",
    "failures": "repair",
    "checks": "check",
    "tests": "test",
}


@unique
class MatchDecision(StrEnum):
    RUN = "run"
    ASK = "ask"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class WorkflowMatch:
    decision: MatchDecision
    confidence: float
    workflow: Workflow
    inputs: dict[str, str]
    reason: str


@dataclass(frozen=True, slots=True)
class MatcherBenchResult:
    workflow_count: int
    duration_seconds: float


class WorkflowMatcher:
    def __init__(self, workflows_dir: Path) -> None:
        self.workflows_dir = workflows_dir

    def best_match(self, request: str, workspace: Path) -> WorkflowMatch:
        workflows = list_workflows(self.workflows_dir)
        candidates = tuple(
            match
            for workflow in workflows
            if (match := _score_workflow(workflow, request, workspace)).decision is not MatchDecision.SKIP
        )
        if not candidates:
            return _empty_match()
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)[0]

    def benchmark(self, request: str, workspace: Path, sizes: tuple[int, ...]) -> tuple[MatcherBenchResult, ...]:
        workflows = list_workflows(self.workflows_dir)
        results: list[MatcherBenchResult] = []
        for size in sizes:
            started = perf_counter()
            for workflow in workflows[:size]:
                _score_workflow(workflow, request, workspace)
            results.append(MatcherBenchResult(size, perf_counter() - started))
        return tuple(results)


def _score_workflow(workflow: Workflow, request: str, workspace: Path) -> WorkflowMatch:
    if not _project_compatible(workflow, workspace):
        return _empty_match(workflow, "project context incompatible")
    inputs = _bind_inputs(workflow.steps, request, workspace)
    if _needs_input(workflow.steps) and not inputs:
        return _empty_match(workflow, "required input unresolved")
    score = _text_score(request, workflow)
    score += _context_bonus(workflow, workspace)
    score = min(score, 1.0)
    if _contains_destructive_step(workflow.steps) and score >= ASK_THRESHOLD:
        return WorkflowMatch(MatchDecision.ASK, score, workflow, inputs, "destructive workflow requires confirmation")
    if score >= RUN_THRESHOLD:
        return WorkflowMatch(MatchDecision.RUN, score, workflow, inputs, "strong deterministic match")
    if score >= ASK_THRESHOLD:
        return WorkflowMatch(MatchDecision.ASK, score, workflow, inputs, "possible deterministic match")
    return _empty_match(workflow, "low confidence")


def _text_score(request: str, workflow: Workflow) -> float:
    request_tokens = _tokens(request)
    haystack = " ".join((workflow.name, workflow.description, " ".join(workflow.tags), " ".join(workflow.intents)))
    workflow_tokens = _tokens(haystack)
    if not request_tokens or not workflow_tokens:
        return 0.0
    overlap = len(request_tokens & workflow_tokens) / len(request_tokens | workflow_tokens)
    contains = 0.35 if workflow.name.replace("-", " ") in _normalize(request) else 0.0
    return overlap + contains


def _context_bonus(workflow: Workflow, workspace: Path) -> float:
    context = _project_context(workspace)
    if not workflow.project_types:
        return 0.0
    overlap = set(workflow.project_types) & context
    if not overlap:
        return 0.0
    bonus = 0.2 * (len(overlap) / len(workflow.project_types))
    if "uv" in workflow.project_types and "uv" in context:
        bonus += 0.12
    return bonus


def _project_compatible(workflow: Workflow, workspace: Path) -> bool:
    required = set(workflow.project_types)
    if not required:
        return True
    return bool(required & _project_context(workspace))


def _project_context(workspace: Path) -> set[str]:
    values: set[str] = set()
    if (workspace / "pyproject.toml").exists() or (workspace / "pytest.ini").exists():
        values.add("python")
    if (workspace / "package.json").exists():
        values.add("node")
    if (workspace / "uv.lock").exists():
        values.update(("python", "uv"))
    if (workspace / "poetry.lock").exists():
        values.update(("python", "poetry"))
    return values


def _bind_inputs(steps: tuple[WorkflowStep, ...], request: str, workspace: Path) -> dict[str, str]:
    if not _needs_input(steps):
        return {}
    references = parse_references(request, workspace)
    for reference in references:
        match reference.kind:
            case ReferenceKind.FILE | ReferenceKind.DIRECTORY:
                return {"target": reference.value}
            case ReferenceKind.GIT_DIFF:
                continue
    for token in request.split():
        path = workspace / token
        if path.exists():
            return {"target": token}
    return {}


def _needs_input(steps: tuple[WorkflowStep, ...]) -> bool:
    return any("{target}" in step.argument or "{target}" in step.content for step in steps)


def _contains_destructive_step(steps: tuple[WorkflowStep, ...]) -> bool:
    return any(step.tool in DESTRUCTIVE_TOOLS for step in steps)


def _tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9가-힣]+", _normalize(value)):
        if raw in STOPWORDS:
            continue
        token = SYNONYMS.get(raw, raw)
        tokens.add(token)
    return tokens


def _normalize(value: str) -> str:
    return value.lower().replace("-", " ")


def _empty_match(workflow: Workflow | None = None, reason: str = "") -> WorkflowMatch:
    empty = workflow or Workflow(name="", description="", steps=())
    return WorkflowMatch(MatchDecision.SKIP, 0.0, empty, {}, reason)
