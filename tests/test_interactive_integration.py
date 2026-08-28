from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction, Prompter
from sovyn.providers import MockProvider
from sovyn.storage import Store, trajectory_for_session
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.workflow_runner import run_workflow


@dataclass(frozen=True, slots=True)
class ScriptedPrompter:
    answers: tuple[str, ...]

    def ask(self, prompt: str) -> str:
        return self.answers[0]


def test_mock_agent_writes_file_records_session_and_replays_workflow(tmp_path: Path) -> None:
    store = Store(tmp_path / ".sovyn" / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    stream = StringIO()
    interaction = Interaction(DEFAULT_CONFIG, Renderer(stream, interactive=False), ScriptedPrompter(("y",)), trust, True)
    runtime = AgentRuntime(MockProvider(), store, interaction.renderer, tmp_path, interaction)

    result = run_agent("create a file called hello.txt containing hello", runtime)
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert trajectory_for_session(store, result.session_id)[-1].name == "filesystem.write"
    assert result.workflow is not None

    from sovyn.workflows import save_workflow

    workflow_path = tmp_path / ".sovyn" / "workflows" / "hello.yaml"
    save_workflow(workflow_path, result.workflow)
    (tmp_path / "hello.txt").unlink()

    replay = run_workflow(workflow_path, tmp_path, store, interaction.renderer, interaction)

    assert replay.tool_calls == 1
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"


def test_permission_always_grant_is_reused(tmp_path: Path) -> None:
    store = Store(tmp_path / ".sovyn" / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(DEFAULT_CONFIG, Renderer(StringIO(), interactive=False), ScriptedPrompter(("a",)), trust, True)
    runtime = AgentRuntime(MockProvider(), store, interaction.renderer, tmp_path, interaction)

    first = run_agent("create a file called hello.txt containing hello", runtime)
    second = run_agent("create a file called hello.txt containing hello", runtime)

    assert first.tools[-1].name == "filesystem.write"
    assert second.tools[-1].name == "filesystem.write"
