from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from typer.testing import CliRunner

from sovyn.agent import AgentRuntime, run_agent
from sovyn.commands import SlashCommand, parse_slash_command
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Approval, Interaction
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.references import ReferenceKind, parse_references
from sovyn.repl import render_help
from sovyn.runtime import boot
from sovyn.stats import local_stats
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.trajectory import compile_trajectory
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.undo import describe_history, describe_last_undo, restore_last_change
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import StepKind, workflow_path


@dataclass(slots=True)  # noqa
class QueuePrompter:
    answers: list[str]
    prompts: list[str]

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)  # noqa
class ScriptedProvider:
    calls: tuple[ToolCall, ...]
    turn_count: int = 0

    @property
    def name(self) -> str:
        return "test/scripted"

    async def generate(self, prompt: str) -> str:
        return "done"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "done"

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.turn_count += 1
        if self.turn_count <= len(self.calls):
            return ProviderTurn("", (self.calls[self.turn_count - 1],))
        return ProviderTurn("done")


def _interaction(tmp_path: Path, prompter: QueuePrompter | None = None) -> tuple[Store, Interaction]:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    renderer = Renderer(StringIO(), interactive=False)
    return store, Interaction(DEFAULT_CONFIG, renderer, prompter or QueuePrompter(["y"], []), trust, True)


def test_parse_slash_command_accepts_known_surface() -> None:
    command = parse_slash_command("/status now")

    assert command == SlashCommand.STATUS


def test_help_fits_one_screen() -> None:
    lines = render_help().splitlines()

    assert "/permissions" in render_help()
    assert len(lines) <= 18


def test_at_references_parse_file_directory_and_git_diff(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# SOVYN\n", encoding="utf-8")
    (tmp_path / "src").mkdir()

    references = parse_references("@README.md @src @git:diff explain", tmp_path)

    assert tuple(item.kind for item in references) == (
        ReferenceKind.FILE,
        ReferenceKind.DIRECTORY,
        ReferenceKind.GIT_DIFF,
    )
    assert references[0].value == "README.md"


def test_task_level_permission_grant_reuses_current_task_only(tmp_path: Path) -> None:
    _, interaction = _interaction(tmp_path, QueuePrompter(["a"], []))
    request = PermissionRequest(
        ActionKind.WRITE_FILES,
        "Create or modify summary.txt",
        reason="Update requested output file",
    )

    first = interaction.approve(request)
    second = interaction.approve(request)
    _, next_interaction = _interaction(tmp_path, QueuePrompter(["n"], []))
    third = next_interaction.approve(request)

    assert first is Approval.TASK
    assert second is Approval.TASK
    assert third is Approval.DENY


def test_permission_prompt_includes_reason(tmp_path: Path) -> None:
    stream = StringIO()
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    prompter = QueuePrompter(["n"], [])
    interaction = Interaction(DEFAULT_CONFIG, Renderer(stream, interactive=False), prompter, trust, True)

    interaction.approve(
        PermissionRequest(ActionKind.WRITE_FILES, "Create or modify summary.txt", reason="Save task result")
    )

    assert "Reason" in stream.getvalue()
    assert "Save task result" in stream.getvalue()


def test_write_tool_records_undo_and_restores_previous_user_content(tmp_path: Path) -> None:
    path = tmp_path / "summary.txt"
    path.write_text("user draft", encoding="utf-8")
    store, interaction = _interaction(tmp_path, QueuePrompter(["y"], []))
    provider = ScriptedProvider((ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN"}),))

    run_agent("update summary", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))
    assert "summary.txt" in describe_last_undo(store)
    restored = restore_last_change(store, tmp_path)

    assert restored == (path,)
    assert path.read_text(encoding="utf-8") == "user draft"


def test_undo_deletes_created_file(tmp_path: Path) -> None:
    store, interaction = _interaction(tmp_path, QueuePrompter(["y"], []))
    provider = ScriptedProvider((ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN"}),))

    run_agent("create summary", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))
    restored = restore_last_change(store, tmp_path)

    assert restored == (tmp_path / "summary.txt",)
    assert not (tmp_path / "summary.txt").exists()


def test_completion_summary_omits_workflow_prompt(tmp_path: Path) -> None:
    store, interaction = _interaction(tmp_path)
    stream = interaction.renderer.stream
    provider = ScriptedProvider((ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN"}),))

    run_agent("create summary", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))
    output = stream.getvalue()

    assert "Done" in output
    assert "Changed" in output
    assert "Create workflow" not in output


def test_trajectory_compiler_classifies_steps_and_generates_open_workflow(tmp_path: Path) -> None:
    calls = (
        ToolCall("read-1", "filesystem.read", {"path": "README.md"}),
        ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN"}),
        ToolCall("http-1", "http.get", {"url": "https://example.com"}),
    )

    workflow = compile_trajectory("summarize @README.md", calls)

    assert tuple(step.kind for step in workflow.steps) == (
        StepKind.PARAMETERIZED,
        StepKind.PARAMETERIZED,
        StepKind.MODEL_REQUIRED,
    )
    assert workflow.version == 1
    assert ActionKind.WRITE_FILES.value in workflow.permissions
    assert workflow.network is True


def test_zero_model_workflow_replay_records_stats(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    workflow = compile_trajectory("list files", (ToolCall("list-1", "filesystem.list", {}),))
    path = workflow_path(tmp_path, "list-files")
    from sovyn.workflows import save_workflow

    save_workflow(path, workflow)
    _, interaction = _interaction(tmp_path, QueuePrompter(["y"], []))

    result = run_workflow(path, tmp_path, store, Renderer(StringIO(), interactive=False), interaction)
    stats = local_stats(store)

    assert result.model_calls == 0
    assert stats.zero_model_runs == 1
    assert stats.workflows_reused == 1


def test_history_lists_recent_sovyn_changes(tmp_path: Path) -> None:
    store, interaction = _interaction(tmp_path, QueuePrompter(["y"], []))
    provider = ScriptedProvider((ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN"}),))

    run_agent("create summary", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert "create summary" in describe_history(store)


def test_startup_rendering_is_compact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    stream = StringIO()

    runtime = boot(StringIO(""), stream, interactive=False, workspace=tmp_path)

    assert runtime.paths.workspace == tmp_path
    assert stream.getvalue() == ""


def test_cli_smoke_help_command_is_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(parse_cli_app(), ["version"])

    assert result.exit_code == 0


def parse_cli_app():
    from sovyn.cli import app

    return app
