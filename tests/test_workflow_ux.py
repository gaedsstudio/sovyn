from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.cli import workflow_show
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.storage import Store
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.workflows import StepKind, Workflow, WorkflowStep, save_workflow, workflow_path


@dataclass(slots=True)  # noqa
class QueuePrompter:
    answers: list[str]
    prompts: list[str]

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


def _interaction(tmp_path: Path, prompter: QueuePrompter) -> Interaction:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    return Interaction(DEFAULT_CONFIG, Renderer(StringIO(), interactive=False), prompter, trust, True)


def _workflow() -> Workflow:
    return Workflow("hello", "demo", (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "write"),))


@pytest.mark.parametrize("answer", ("", "n", "no", "exit", "quit", "cancel", "maybe"))
def test_workflow_offer_is_safe_opt_in_when_answer_is_not_yes(tmp_path: Path, answer: str) -> None:
    prompter = QueuePrompter([answer], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is False
    assert prompter.prompts == ["Learn this task? [y/N] "]
    assert not tuple((tmp_path / "workflows").glob("*.yaml"))


@pytest.mark.parametrize("answer", ("y", "yes"))
def test_workflow_offer_asks_name_only_after_explicit_yes(tmp_path: Path, answer: str) -> None:
    prompter = QueuePrompter([answer, "hello-flow"], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is True
    assert prompter.prompts == ["Learn this task? [y/N] ", "Workflow name [hello]: "]
    assert (tmp_path / "workflows" / "hello-flow.yaml").exists()


def test_workflow_offer_uses_safe_default_name_when_name_is_blank(tmp_path: Path) -> None:
    prompter = QueuePrompter(["y", ""], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is True
    assert (tmp_path / "workflows" / "hello.yaml").exists()


def test_workflow_offer_rejects_path_traversal_name(tmp_path: Path) -> None:
    prompter = QueuePrompter(["y", "../escape"], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is False
    assert not (tmp_path / "escape.yaml").exists()


def test_workflow_show_displays_inspection_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys) -> None:
    paths = _paths(tmp_path)
    workflow = Workflow(
        "inspectable",
        "demo workflow",
        (WorkflowStep("filesystem.write", StepKind.DETERMINISTIC, "write", "out.txt", "ok"),),
        permissions=("write_files",),
        model_required=False,
        validation=("all deterministic steps must succeed",),
    )
    save_workflow(workflow_path(paths.workflows, workflow.name), workflow)
    monkeypatch.setattr("sovyn.cli.default_paths", lambda: paths)

    workflow_show("inspectable")

    output = capsys.readouterr().out
    assert "model_required: false" in output
    assert "permissions: write_files" in output
    assert "validation: all deterministic steps must succeed" in output
    assert "01 filesystem.write deterministic out.txt" in output


def _paths(tmp_path: Path):
    from sovyn.paths import default_paths

    paths = default_paths(home=tmp_path / "home", workspace=tmp_path)
    paths.ensure()
    return paths
