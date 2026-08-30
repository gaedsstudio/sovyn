from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.matcher import MatchDecision, WorkflowMatcher
from sovyn.permissions import ActionKind
from sovyn.stats import local_stats
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import StepKind, Workflow, WorkflowStep, save_workflow, workflow_path


@dataclass(slots=True)  # noqa: MUTABLE_OK
class QueuePrompter:
    answers: list[str]

    def ask(self, prompt: str) -> str:
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)  # noqa: MUTABLE_OK
class FailingProvider:
    calls: int = 0

    @property
    def name(self) -> str:
        return "test/failing"

    async def generate(self, prompt: str) -> str:
        self.calls += 1
        raise AssertionError("provider must not be called")

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.calls += 1
        raise AssertionError("provider must not be called")
        yield ""

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.calls += 1
        raise AssertionError("provider must not be called")


def _interaction(tmp_path: Path, answers: list[str] | None = None) -> tuple[Store, Interaction, StringIO]:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    stream = StringIO()
    interaction = Interaction(DEFAULT_CONFIG, Renderer(stream, interactive=False), QueuePrompter(answers or ["y"]), trust, True)
    return store, interaction, stream


def _workflow(
    name: str,
    description: str,
    steps: tuple[WorkflowStep, ...],
    project_types: tuple[str, ...] = (),
    permissions: tuple[str, ...] = (),
) -> Workflow:
    return Workflow(
        name=name,
        description=description,
        steps=steps,
        permissions=permissions,
        project_types=project_types,
        origin="learned_local",
    )


def test_exact_workflow_match_scores_high(tmp_path: Path) -> None:
    workflow = _workflow("release-check", "run release checks", (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),))
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)

    match = WorkflowMatcher(tmp_path).best_match("run release checks", tmp_path)

    assert match.decision is MatchDecision.RUN
    assert match.workflow.name == "release-check"


def test_paraphrased_workflow_match_runs_without_provider(tmp_path: Path) -> None:
    workflow = _workflow("release-check", "run release checks", (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),))
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, stream = _interaction(tmp_path)
    provider = FailingProvider()

    result = run_agent(
        "please do the release check",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction, workflows_dir=tmp_path),
    )

    assert provider.calls == 0
    assert result.model_calls == 0
    assert "Reusing · release-check" in stream.getvalue()


def test_unrelated_request_does_not_match(tmp_path: Path) -> None:
    workflow = _workflow("release-check", "run release checks", (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),))
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)

    match = WorkflowMatcher(tmp_path).best_match("write a product announcement", tmp_path)

    assert match.decision is MatchDecision.SKIP


def test_project_incompatible_workflow_is_rejected(tmp_path: Path) -> None:
    workflow = _workflow(
        "python-test-repair",
        "run tests and fix failures",
        (WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run tests", argument="pytest"),),
        project_types=("python",),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)

    match = WorkflowMatcher(tmp_path).best_match("tests broke again fix them", tmp_path)

    assert match.decision is MatchDecision.SKIP


def test_at_file_input_binding_replays_runtime_target(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("old", encoding="utf-8")
    workflow = _workflow(
        "update-target",
        "update target file",
        (WorkflowStep("filesystem.write", StepKind.PARAMETERIZED, "Write target", argument="{target}", content="new"),),
        permissions=(ActionKind.WRITE_FILES.value,),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, _ = _interaction(tmp_path, ["y"])

    result = run_workflow(
        workflow_path(tmp_path, workflow.name),
        tmp_path,
        store,
        Renderer(StringIO(), interactive=False),
        interaction,
        inputs={"target": "README.md"},
    )

    assert result.model_calls == 0
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "new"


def test_medium_confidence_requires_confirmation(tmp_path: Path) -> None:
    workflow = _workflow("release-check", "run release checks", (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),))
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    match = WorkflowMatcher(tmp_path).best_match("check release", tmp_path)

    assert match.decision is MatchDecision.ASK


def test_destructive_workflow_requires_confirmation(tmp_path: Path) -> None:
    workflow = _workflow(
        "cleanup",
        "clean generated files",
        (WorkflowStep("filesystem.delete", StepKind.DETERMINISTIC, "Delete generated file", "out.txt"),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    match = WorkflowMatcher(tmp_path).best_match("clean generated files", tmp_path)

    assert match.decision is MatchDecision.ASK


def test_missing_input_falls_back_to_agent(tmp_path: Path) -> None:
    workflow = _workflow(
        "update-target",
        "update target file",
        (WorkflowStep("filesystem.write", StepKind.PARAMETERIZED, "Write target", argument="{target}", content="new"),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    match = WorkflowMatcher(tmp_path).best_match("update target file", tmp_path)

    assert match.decision is MatchDecision.SKIP


def test_deterministic_repair_creates_new_variant_and_preserves_old(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    workflow = _workflow(
        "python-test-repair",
        "run tests",
        (WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run tests", argument="pytest-missing-runner"),),
        project_types=("python",),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, stream = _interaction(tmp_path, ["a"])

    result = run_workflow(
        workflow_path(tmp_path, workflow.name),
        tmp_path,
        store,
        Renderer(stream, interactive=False),
        interaction,
        allow_repair=True,
    )

    assert result.evolved is True
    assert result.model_calls == 0
    assert workflow_path(tmp_path, "python-test-repair-v2").exists()
    assert workflow_path(tmp_path, "python-test-repair").exists()


def test_variant_selection_prefers_compatible_context(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    v1 = _workflow(
        "python-test-repair",
        "run tests",
        (WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run tests", argument="pytest"),),
        project_types=("python",),
    )
    v2 = _workflow(
        "python-test-repair-v2",
        "run tests",
        (WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run tests", argument="python --version"),),
        project_types=("python", "uv"),
    )
    save_workflow(workflow_path(tmp_path, v1.name), v1)
    save_workflow(workflow_path(tmp_path, v2.name), v2)

    match = WorkflowMatcher(tmp_path).best_match("tests broke again", tmp_path)

    assert match.workflow.name == "python-test-repair-v2"


def test_replay_enforces_permissions(tmp_path: Path) -> None:
    workflow = _workflow(
        "write-known-file",
        "write known file",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write known file", "known.txt", "ok"),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, _ = _interaction(tmp_path, ["n"])

    result = run_workflow(workflow_path(tmp_path, workflow.name), tmp_path, store, Renderer(StringIO(), False), interaction)

    assert result.tool_calls == 1
    assert result.status == "failed"
    assert not (tmp_path / "known.txt").exists()


def test_stats_include_workflow_intelligence_counters(tmp_path: Path) -> None:
    workflow = _workflow("release-check", "run release checks", (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),))
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, _ = _interaction(tmp_path)

    run_workflow(workflow_path(tmp_path, workflow.name), tmp_path, store, Renderer(StringIO(), False), interaction)
    stats = local_stats(store)

    assert stats.workflow_matches == 1
    assert stats.zero_model_runs == 1


def test_matcher_latency_scales_to_1000_workflows(tmp_path: Path) -> None:
    for index in range(1000):
        workflow = _workflow(
            f"release-check-{index}",
            f"run release checks {index}",
            (WorkflowStep("git.status", StepKind.DETERMINISTIC, ""),),
        )
        save_workflow(workflow_path(tmp_path, workflow.name), workflow)

    result = WorkflowMatcher(tmp_path).benchmark("run release checks", tmp_path, (1, 10, 100, 1000))

    assert tuple(item.workflow_count for item in result) == (1, 10, 100, 1000)
    assert all(item.duration_seconds < 0.5 for item in result)
