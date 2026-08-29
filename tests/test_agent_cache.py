from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction, Prompter
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(frozen=True, slots=True)
class ScriptedPrompter:
    answers: tuple[str, ...]

    def ask(self, prompt: str) -> str:
        return self.answers[0]


@dataclass(slots=True)  # noqa: MUTABLE_OK
class CountingProvider:
    calls: tuple[ToolCall, ...]
    turn_count: int = 0

    @property
    def name(self) -> str:
        return "test/counting"

    async def generate(self, prompt: str) -> str:
        return "done"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "done"

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.turn_count += 1
        if self.turn_count <= len(self.calls):
            return ProviderTurn("", (self.calls[self.turn_count - 1],))
        return ProviderTurn("done")


def _trusted_interaction(tmp_path: Path) -> tuple[Store, Interaction]:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    renderer = Renderer(StringIO(), interactive=False)
    return store, Interaction(DEFAULT_CONFIG, renderer, ScriptedPrompter(("y",)), trust, True)


def test_duplicate_read_reuses_successful_result_without_workspace_mutation(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# SOVYN\n", encoding="utf-8")
    store, interaction = _trusted_interaction(tmp_path)
    provider = CountingProvider(
        (
            ToolCall("read-1", "filesystem.read", {"path": "README.md"}),
            ToolCall("read-2", "filesystem.read", {"path": "README.md"}),
        )
    )
    observed: list[Path] = []

    def counting_read(path: Path):
        observed.append(path)
        from sovyn.tools import read_file

        return read_file(path)

    monkeypatch.setattr("sovyn.tool_registry.read_file", counting_read)

    result = run_agent("read README twice", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert len(observed) == 1
    assert tuple(tool.tool_call_id for tool in result.tools if tool.name == "filesystem.read") == ("read-1", "read-2")


def test_duplicate_read_can_continue_to_write_without_loop_guard_blocking(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# SOVYN Test\n", encoding="utf-8")
    store, interaction = _trusted_interaction(tmp_path)
    provider = CountingProvider(
        (
            ToolCall("read-1", "filesystem.read", {"path": "README.md"}),
            ToolCall("read-2", "filesystem.read", {"path": "README.md"}),
            ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "SOVYN Test"}),
        )
    )
    observed: list[Path] = []

    def counting_read(path: Path):
        observed.append(path)
        from sovyn.tools import read_file

        return read_file(path)

    monkeypatch.setattr("sovyn.tool_registry.read_file", counting_read)

    result = run_agent(
        "README.md를 읽고 프로젝트 이름을 확인한 다음 summary.txt에 프로젝트 이름만 저장해줘",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction),
    )

    assert len(observed) == 1
    assert (tmp_path / "summary.txt").read_text(encoding="utf-8") == "SOVYN Test"
    assert "Repeated action detected" not in result.response


def test_infinite_cached_read_stalls_safely_without_executing_again(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# SOVYN Test\n", encoding="utf-8")
    store, interaction = _trusted_interaction(tmp_path)
    provider = CountingProvider(
        (
            ToolCall("read-1", "filesystem.read", {"path": "README.md"}),
            ToolCall("read-2", "filesystem.read", {"path": "README.md"}),
            ToolCall("read-3", "filesystem.read", {"path": "README.md"}),
            ToolCall("read-4", "filesystem.read", {"path": "README.md"}),
        )
    )
    observed: list[Path] = []

    def counting_read(path: Path):
        observed.append(path)
        from sovyn.tools import read_file

        return read_file(path)

    monkeypatch.setattr("sovyn.tool_registry.read_file", counting_read)

    result = run_agent("read README forever", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert len(observed) == 1
    assert result.response == "Model stalled on an already satisfied read-only action."


def test_duplicate_read_refreshes_after_workspace_mutation(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# SOVYN\n", encoding="utf-8")
    store, interaction = _trusted_interaction(tmp_path)
    provider = CountingProvider(
        (
            ToolCall("read-1", "filesystem.read", {"path": "README.md"}),
            ToolCall("write-1", "filesystem.write", {"path": "README.md", "content": "# SOVYN 2\n"}),
            ToolCall("read-2", "filesystem.read", {"path": "README.md"}),
        )
    )
    observed: list[Path] = []

    def counting_read(path: Path):
        observed.append(path)
        from sovyn.tools import read_file

        return read_file(path)

    monkeypatch.setattr("sovyn.tool_registry.read_file", counting_read)

    result = run_agent("read write read", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert len(observed) == 2
    assert result.tools[-1].output == "# SOVYN 2\n"


def test_repeated_mutating_actions_still_trigger_loop_guard(tmp_path: Path) -> None:
    store, interaction = _trusted_interaction(tmp_path)
    provider = CountingProvider(
        (
            ToolCall("write-1", "filesystem.write", {"path": "summary.txt", "content": "one"}),
            ToolCall("write-2", "filesystem.write", {"path": "summary.txt", "content": "one"}),
            ToolCall("write-3", "filesystem.write", {"path": "summary.txt", "content": "one"}),
        )
    )

    result = run_agent("write summary forever", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.response == "Repeated action detected"
    assert (tmp_path / "summary.txt").read_text(encoding="utf-8") == "one"
