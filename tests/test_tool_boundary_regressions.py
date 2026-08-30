from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.agent import AgentRuntime, run_agent
from sovyn.agent_cache import ToolCallCache
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tool_registry import execute_validated_tool, validate_tool_call
from sovyn.tools import ToolResult, git_status, read_file
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(slots=True)
class QueuePrompter:
    answers: list[str]

    def ask(self, prompt: str) -> str:
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)
class ScriptedProvider:
    calls: tuple[ToolCall, ...]
    name: str = "test/scripted"
    turn_count: int = 0

    async def generate(self, prompt: str) -> str:
        return "done"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "done"

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.turn_count += 1
        if self.turn_count == 1:
            return ProviderTurn("", self.calls)
        return ProviderTurn("done")


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


def test_mutating_tools_fail_closed_without_interaction(tmp_path: Path) -> None:
    write = validate_tool_call(ToolCall("write", "filesystem.write", {"path": "x.txt", "content": "x"}))
    shell = validate_tool_call(ToolCall("shell", "shell.run", {"command": "python --version"}))
    network = validate_tool_call(ToolCall("net", "http.get", {"url": "https://example.com"}))

    assert execute_validated_tool(write, tmp_path, None).success is False
    assert execute_validated_tool(shell, tmp_path, None).success is False
    assert execute_validated_tool(network, tmp_path, None).success is False
    assert not (tmp_path / "x.txt").exists()


def test_shell_prompt_mentions_non_undoable_capability(tmp_path: Path) -> None:
    store, interaction, stream = _interaction(tmp_path, ("n",))
    shell = validate_tool_call(ToolCall("shell", "shell.run", {"command": "python --version"}))

    result = execute_validated_tool(shell, tmp_path, interaction)

    assert result.success is False
    assert "may modify files and may not be fully undoable" in stream.getvalue()
    assert store is not None


def test_failed_shell_mutation_invalidates_read_cache(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("old", encoding="utf-8")
    store, interaction, _ = _interaction(tmp_path)
    provider = ScriptedProvider(
        (
            ToolCall("read-1", "filesystem.read", {"path": "data.txt"}),
            ToolCall(
                "shell",
                "shell.run",
                {"command": "python -c \"open('data.txt','w').write('new'); raise SystemExit(1)\""},
            ),
            ToolCall("read-2", "filesystem.read", {"path": "data.txt"}),
        )
    )

    result = run_agent("read shell read", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.tools[-1].output == "new"


def test_cache_reuses_read_but_invalidates_after_shell_success(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("old", encoding="utf-8")
    cache = ToolCallCache()
    read_one = ToolCall("read-1", "filesystem.read", {"path": "data.txt"})
    read_two = ToolCall("read-2", "filesystem.read", {"path": "data.txt"})
    cache.store(read_one, ToolResult("filesystem.read", "read", "old"))

    cache.observe(ToolResult("shell.run", "exit 0", success=True))

    assert cache.result_for(read_two) is None


@pytest.mark.parametrize("payload", (b"\xff\xfe\xfa", b"\x00\x01\x02binary"))
def test_read_file_returns_failure_for_non_text_payload(tmp_path: Path, payload: bytes) -> None:
    target = tmp_path / "bad.bin"
    target.write_bytes(payload)

    result = read_file(target)

    assert result.success is False
    assert "valid UTF-8 text" in result.error


def test_read_file_returns_failure_for_missing_file(tmp_path: Path) -> None:
    result = read_file(tmp_path / "missing.txt")

    assert result.success is False
    assert "not found" in result.error.lower()


def test_git_status_fails_outside_git_repository(tmp_path: Path) -> None:
    result = git_status(tmp_path)

    assert result.success is False
    assert "git" in result.error.lower()
