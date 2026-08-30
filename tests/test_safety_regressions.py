from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.providers import ModelProvider
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import StepKind, Workflow, WorkflowStep, save_workflow, workflow_path


@dataclass(slots=True)
class QueuePrompter:
    answers: list[str]

    def ask(self, prompt: str) -> str:
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)
class FailingProvider:
    calls: int = 0
    name: str = "test/failing"

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


def _interaction(workspace: Path, answers: tuple[str, ...] = ("y",)) -> tuple[Store, Interaction, StringIO]:
    store = Store(workspace / ".sovyn" / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(workspace)
    stream = StringIO()
    interaction = Interaction(
        DEFAULT_CONFIG,
        Renderer(stream, interactive=False),
        QueuePrompter(list(answers)),
        trust,
        True,
    )
    return store, interaction, stream


@pytest.mark.parametrize(
    "raw_path",
    (
        "../outside.txt",
        "../../outside.txt",
        "C:\\outside.txt",
        "C:/outside.txt",
        "\\\\server\\share",
        "/workspace/../outside",
    ),
)
def test_workflow_write_rejects_workspace_escape(tmp_path: Path, raw_path: str) -> None:
    workspace = tmp_path / "repo"
    workflows = tmp_path / "flows"
    workspace.mkdir()
    workflow = Workflow(
        "escape",
        "write outside",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write outside", raw_path, "escaped"),),
    )
    save_workflow(workflow_path(workflows, workflow.name), workflow)
    store, interaction, stream = _interaction(workspace)

    result = run_workflow(workflow_path(workflows, workflow.name), workspace, store, Renderer(stream), interaction)

    assert result.status == "failed"
    assert not (tmp_path / "outside.txt").exists()


@pytest.mark.parametrize(
    "raw_path",
    ("unicode/요약.txt", "space dir/report final.txt", "nested/allowed/file.txt", "normal.txt"),
)
def test_workflow_write_allows_safe_relative_paths(tmp_path: Path, raw_path: str) -> None:
    workflows = tmp_path / "flows"
    workflow = Workflow(
        "safe-write",
        "write safe",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write safe", raw_path, "ok"),),
    )
    save_workflow(workflow_path(workflows, workflow.name), workflow)
    store, interaction, stream = _interaction(tmp_path)

    result = run_workflow(workflow_path(workflows, workflow.name), tmp_path, store, Renderer(stream), interaction)

    assert result.status == "success"
    assert (tmp_path / raw_path).read_text(encoding="utf-8") == "ok"


def test_symlink_write_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    workspace = tmp_path / "repo"
    workflows = tmp_path / "flows"
    outside.mkdir()
    workspace.mkdir()
    link = workspace / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    workflow = Workflow(
        "symlink-escape",
        "write through symlink",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write through symlink", "link/escaped.txt", "bad"),),
    )
    save_workflow(workflow_path(workflows, workflow.name), workflow)
    store, interaction, stream = _interaction(workspace)

    result = run_workflow(workflow_path(workflows, workflow.name), workspace, store, Renderer(stream), interaction)

    assert result.status == "failed"
    assert not (outside / "escaped.txt").exists()


def test_failed_workflow_reports_failed_not_completed(tmp_path: Path) -> None:
    workflow = Workflow(
        "bad-shell",
        "run bad shell",
        (WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run bad shell", "python -c \"raise SystemExit(7)\""),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, stream = _interaction(tmp_path)

    result = run_workflow(workflow_path(tmp_path, workflow.name), tmp_path, store, Renderer(stream), interaction)

    assert result.status == "failed"
    assert "Workflow failed" in stream.getvalue()
    assert "Workflow completed" not in stream.getvalue()


def test_denied_replay_does_not_call_provider_or_mutate(tmp_path: Path) -> None:
    workflow = Workflow(
        "write-known-file",
        "write known file",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write known file", "known.txt", "ok"),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, stream = _interaction(tmp_path, ("n",))
    provider = FailingProvider()

    result = run_agent(
        "write known file",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction, workflows_dir=tmp_path),
    )

    assert provider.calls == 0
    assert result.model_calls == 0
    assert result.response == "Workflow failed"
    assert "write denied" in stream.getvalue()
    assert not (tmp_path / "known.txt").exists()


def test_zero_model_replay_still_succeeds_with_permission(tmp_path: Path) -> None:
    workflow = Workflow(
        "write-known-file",
        "write known file",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "Write known file", "known.txt", "ok"),),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction, _ = _interaction(tmp_path, ("y",))
    provider: ModelProvider = FailingProvider()

    result = run_agent(
        "write known file",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction, workflows_dir=tmp_path),
    )

    assert result.model_calls == 0
    assert result.response == "Workflow completed"
    assert (tmp_path / "known.txt").read_text(encoding="utf-8") == "ok"
