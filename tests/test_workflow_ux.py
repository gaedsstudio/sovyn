from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction, Prompter
from sovyn.storage import Store
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.workflows import StepKind, Workflow, WorkflowStep


@dataclass(slots=True)  # noqa: MUTABLE_OK
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
    assert prompter.prompts == ["Create workflow? [y/N] "]
    assert not tuple((tmp_path / "workflows").glob("*.yaml"))


@pytest.mark.parametrize("answer", ("y", "yes"))
def test_workflow_offer_asks_name_only_after_explicit_yes(tmp_path: Path, answer: str) -> None:
    prompter = QueuePrompter([answer, "hello-flow"], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is True
    assert prompter.prompts == ["Create workflow? [y/N] ", "Workflow name: "]
    assert (tmp_path / "workflows" / "hello-flow.yaml").exists()


def test_workflow_offer_rejects_path_traversal_name(tmp_path: Path) -> None:
    prompter = QueuePrompter(["y", "../escape"], [])
    interaction = _interaction(tmp_path, prompter)

    saved = interaction.offer_workflow(_workflow(), tmp_path / "workflows")

    assert saved is False
    assert not (tmp_path / "escape.yaml").exists()
