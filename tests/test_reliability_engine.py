from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.agent import AgentRuntime, RunStatus, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.provider_wire import ProviderError, ProviderErrorKind
from sovyn.sessions import get_session
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tool_registry import execute_validated_tool, validate_tool_call
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(slots=True)  # noqa: MUTABLE_OK
class QueuePrompter:
    answers: list[str]
    prompts: list[str]

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)  # noqa: MUTABLE_OK
class ScriptedProvider:
    turns: tuple[ProviderTurn, ...]
    turn_count: int = 0

    @property
    def name(self) -> str:
        return "test/reliability"

    async def generate(self, prompt: str) -> str:
        return "done"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "done"

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.turn_count += 1
        if self.turn_count <= len(self.turns):
            return self.turns[self.turn_count - 1]
        return ProviderTurn("done")


@dataclass(frozen=True, slots=True)
class FailingProvider:
    @property
    def name(self) -> str:
        return "test/failing"

    async def generate(self, prompt: str) -> str:
        raise ProviderError(ProviderErrorKind.NETWORK_ERROR, "test", "offline")

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        raise ProviderError(ProviderErrorKind.NETWORK_ERROR, "test", "offline")
        yield ""

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        raise ProviderError(ProviderErrorKind.NETWORK_ERROR, "test", "offline")


def _runtime(
    tmp_path: Path, stream: StringIO | None = None, prompter: QueuePrompter | None = None
) -> tuple[Store, Interaction]:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    renderer = Renderer(stream or StringIO(), interactive=False)
    return store, Interaction(DEFAULT_CONFIG, renderer, prompter or QueuePrompter(["y"], []), trust, True)


def test_identical_write_is_no_op_without_second_permission(tmp_path: Path) -> None:
    store, interaction = _runtime(tmp_path, prompter=QueuePrompter(["y"], []))
    provider = ScriptedProvider(
        (
            ProviderTurn(
                "", (ToolCall("write-1", "filesystem.write", {"path": "hello.txt", "content": "Hello from SOVYN"}),)
            ),
            ProviderTurn(
                "", (ToolCall("write-2", "filesystem.write", {"path": "hello.txt", "content": "Hello from SOVYN"}),)
            ),
            ProviderTurn("done"),
        )
    )

    result = run_agent(
        "hello.txt 파일을 만들고 Hello from SOVYN 이라고 작성해줘",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction),
    )

    writes = tuple(tool for tool in result.tools if tool.name == "filesystem.write")
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "Hello from SOVYN"
    assert tuple(tool.no_change for tool in writes) == (False, True)
    assert interaction.prompter.prompts == ["[a] task  [y] once  [n] deny: "]
    assert result.status is RunStatus.SUCCESS


def test_different_second_write_still_requires_permission(tmp_path: Path) -> None:
    store, interaction = _runtime(tmp_path, prompter=QueuePrompter(["y", "y"], []))
    provider = ScriptedProvider(
        (
            ProviderTurn("", (ToolCall("write-1", "filesystem.write", {"path": "hello.txt", "content": "one"}),)),
            ProviderTurn("", (ToolCall("write-2", "filesystem.write", {"path": "hello.txt", "content": "two"}),)),
            ProviderTurn("done"),
        )
    )

    result = run_agent(
        "write hello.txt twice with final content two",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction),
    )

    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "two"
    assert len(interaction.prompter.prompts) == 2
    assert result.status is RunStatus.SUCCESS


def test_provider_error_is_not_success_or_workflow(tmp_path: Path) -> None:
    stream = StringIO()
    store, interaction = _runtime(tmp_path, stream=stream)

    result = run_agent(
        "create hello.txt", AgentRuntime(FailingProvider(), store, interaction.renderer, tmp_path, interaction)
    )
    session = get_session(store, result.session_id)

    assert result.status is RunStatus.PROVIDER_ERROR
    assert result.workflow is None
    assert session is not None
    assert session.result == "provider_error"
    assert "◆ Done" not in stream.getvalue()
    assert "× Provider unavailable" in stream.getvalue()


def test_text_only_action_claim_is_failed(tmp_path: Path) -> None:
    stream = StringIO()
    store, interaction = _runtime(tmp_path, stream=stream)
    provider = ScriptedProvider((ProviderTurn("I created hello.txt."),))

    result = run_agent("create hello.txt", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.status is RunStatus.FAILED
    assert result.workflow is None
    assert not (tmp_path / "hello.txt").exists()
    assert "× Failed" in stream.getvalue()


def test_step_limit_is_not_success_or_workflow(tmp_path: Path) -> None:
    store, interaction = _runtime(tmp_path)
    limited = DEFAULT_CONFIG.agent.max_steps + 1
    provider = ScriptedProvider(
        tuple(
            ProviderTurn("", (ToolCall(f"search-{index}", "workspace.search", {"term": f"missing-{index}"}),))
            for index in range(limited)
        )
    )

    result = run_agent("search until done", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.status is RunStatus.STEP_LIMIT
    assert result.workflow is None


def test_filesystem_write_permission_error_is_contained(tmp_path: Path, monkeypatch) -> None:
    store, interaction = _runtime(tmp_path)
    call = validate_tool_call(ToolCall("write-1", "filesystem.write", {"path": "blocked.txt", "content": "x"}))

    def raise_permission_error(path: Path, content: str):
        raise PermissionError("blocked")

    monkeypatch.setattr("sovyn.tool_registry.write_file", raise_permission_error)

    result = execute_validated_tool(call, tmp_path, interaction)

    assert result.success is False
    assert "blocked" in result.error


def test_filesystem_write_timing_separates_permission_wait(tmp_path: Path, monkeypatch) -> None:
    store, interaction = _runtime(tmp_path)
    call = validate_tool_call(ToolCall("write-1", "filesystem.write", {"path": "timed.txt", "content": "x"}))
    ticks = iter((0.0, 10.0, 10.0, 10.02))

    monkeypatch.setattr("sovyn.tool_registry.perf_counter", lambda: next(ticks))

    result = execute_validated_tool(call, tmp_path, interaction)

    assert result.success is True
    assert result.permission_wait_seconds == pytest.approx(10.0)
    assert result.execution_seconds == pytest.approx(0.02)


def test_changed_path_ui_deduplicates_repeated_no_op_write(tmp_path: Path) -> None:
    stream = StringIO()
    store, interaction = _runtime(tmp_path, stream=stream, prompter=QueuePrompter(["y"], []))
    provider = ScriptedProvider(
        (
            ProviderTurn("", (ToolCall("write-1", "filesystem.write", {"path": "hello.txt", "content": "Hello"}),)),
            ProviderTurn("", (ToolCall("write-2", "filesystem.write", {"path": "hello.txt", "content": "Hello"}),)),
            ProviderTurn("done"),
        )
    )

    result = run_agent("create hello.txt", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.status is RunStatus.SUCCESS
    changed_summary = stream.getvalue().split("Changed\n", maxsplit=1)[1].split("Time\n", maxsplit=1)[0]
    assert changed_summary.count("hello.txt\n") == 1


def test_successful_read_only_task_can_still_succeed(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello SOVYN\n", encoding="utf-8")
    store, interaction = _runtime(tmp_path)
    provider = ScriptedProvider(
        (
            ProviderTurn("", (ToolCall("read-1", "filesystem.read", {"path": "README.md"}),)),
            ProviderTurn("README says Hello SOVYN."),
        )
    )

    result = run_agent("README.md를 읽어줘", AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction))

    assert result.status is RunStatus.SUCCESS
    assert result.workflow is not None
