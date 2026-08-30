from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from io import StringIO
from pathlib import Path

import pytest

from sovyn.agent import AgentRuntime, RunStatus, run_agent
from sovyn.assist.language import direct_identity_answer, prepare_request, preserve_literals
from sovyn.config import (
    DEFAULT_CONFIG,
    InterfaceLanguage,
    InterfaceSettings,
    load_config,
    write_config,
)
from sovyn.interaction import Interaction
from sovyn.runtime import boot
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(slots=True)
class SequenceProvider:
    turns: list[ProviderTurn]
    generated: str = "복구된 최종 답변입니다."
    name: str = "ollama/qwen3:1.7b"
    prompts: list[str] = field(default_factory=list)
    generate_prompts: list[str] = field(default_factory=list)

    async def generate(self, prompt: str) -> str:
        self.generate_prompts.append(prompt)
        return self.generated

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def turn(self, prompt: str, tools: tuple) -> ProviderTurn:
        self.prompts.append(prompt)
        if self.turns:
            return self.turns.pop(0)
        return ProviderTurn("")


@dataclass(frozen=True, slots=True)
class ScriptedPrompter:
    answers: tuple[str, ...]

    def ask(self, prompt: str) -> str:
        return self.answers[0]


def test_interface_language_config_backward_compatibility(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.config.write_text('[model]\nprovider = "mock"\n', encoding="utf-8")

    config = load_config(paths)

    assert config.interface.language is InterfaceLanguage.AUTO
    assert config.interface.language_selected is False


def test_language_persistence(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    config = replace(DEFAULT_CONFIG, interface=InterfaceSettings(InterfaceLanguage.KO, True))

    write_config(paths.config, config)

    assert load_config(paths).interface.language is InterfaceLanguage.KO
    assert load_config(paths).interface.language_selected is True


def test_non_interactive_boot_does_not_block_on_onboarding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    runtime = boot(StringIO(""), StringIO(), interactive=False, workspace=tmp_path)

    assert runtime.config.interface.language is InterfaceLanguage.AUTO


def test_interactive_onboarding_persists_language(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    output = StringIO()

    runtime = boot(StringIO("1\n"), output, interactive=True, workspace=tmp_path)

    assert runtime.config.interface.language is InterfaceLanguage.KO
    assert "Language set to 한국어" in output.getvalue()


def test_identity_and_model_intents_are_distinct() -> None:
    identity = direct_identity_answer("너는 누구니?", InterfaceLanguage.KO, "ollama/qwen3:1.7b")
    model = direct_identity_answer("지금 무슨 모델 쓰고 있어?", InterfaceLanguage.KO, "ollama/qwen3:1.7b")

    assert identity is not None and "SOVYN" in identity and "Qwen" not in identity
    assert model is not None and "ollama/qwen3:1.7b" in model


def test_configured_korean_language_contributes_to_prompt_instruction(tmp_path: Path) -> None:
    provider = SequenceProvider([ProviderTurn("완료")])
    config = replace(DEFAULT_CONFIG, interface=InterfaceSettings(InterfaceLanguage.KO, True))
    runtime = _runtime(tmp_path, provider, config)

    run_agent("README.md를 읽어줘", runtime)

    assert "Final answer language: 한국어" in provider.prompts[0]


def test_literal_paths_code_and_commands_are_preserved() -> None:
    request = "agent.py 수정하고 pytest -q 실행해줘"
    prepared = prepare_request(request, DEFAULT_CONFIG, "ollama/qwen3:1.7b")

    assert "agent.py" in prepared.prompt
    assert "pytest -q" in prepared.prompt
    assert "agent.py" in preserve_literals(request)


def test_duplicate_read_triggers_bounded_final_recovery(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# SOVYN\n", encoding="utf-8")
    read = ToolCall("read", "filesystem.read", {"path": "README.md"})
    provider = SequenceProvider(
        [ProviderTurn("", (read,)), ProviderTurn("", (read,)), ProviderTurn("", (read,)), ProviderTurn("", (read,))]
    )

    result = run_agent("README.md를 읽고 한 문장으로 요약해줘", _runtime(tmp_path, provider))

    assert result.status is RunStatus.SUCCESS
    assert result.response == "복구된 최종 답변입니다."
    assert len(provider.generate_prompts) == 1
    assert result.model_calls == 5


def test_duplicate_write_is_physical_once_and_no_second_permission(tmp_path: Path) -> None:
    write = ToolCall("write", "filesystem.write", {"path": "telegram-test.txt", "content": "Hello from Telegram"})
    provider = SequenceProvider([ProviderTurn("", (write,)), ProviderTurn("", (write,)), ProviderTurn("", (write,))])
    runtime = _runtime(tmp_path, provider, answers=("y",))

    result = run_agent("create a file called telegram-test.txt containing Hello from Telegram", runtime)

    assert result.status is RunStatus.SUCCESS
    assert (tmp_path / "telegram-test.txt").read_text(encoding="utf-8") == "Hello from Telegram"
    assert tuple(tool.no_change for tool in result.tools if tool.name == "filesystem.write") == (False, True)


def test_korean_exact_write_can_be_verified_after_repeat(tmp_path: Path) -> None:
    write = ToolCall("write", "filesystem.write", {"path": "telegram-test.txt", "content": "Hello from Telegram"})
    provider = SequenceProvider([ProviderTurn("", (write,)), ProviderTurn("", (write,)), ProviderTurn("", (write,))])

    result = run_agent(
        "telegram-test.txt 파일을 만들고 Hello from Telegram 이라고 작성해줘",
        _runtime(tmp_path, provider, answers=("y",)),
    )

    assert result.status is RunStatus.SUCCESS
    assert (tmp_path / "telegram-test.txt").read_text(encoding="utf-8") == "Hello from Telegram"


def test_recovery_is_bounded_and_stalled_remains_stalled_when_no_evidence(tmp_path: Path) -> None:
    call = ToolCall("bad", "workspace.search", {"term": "nothing"})
    provider = SequenceProvider(
        [ProviderTurn("", (call,)), ProviderTurn("", (call,)), ProviderTurn("", (call,)), ProviderTurn("", (call,))]
    )

    result = run_agent("search repeatedly", _runtime(tmp_path, provider))

    assert result.status is RunStatus.STALLED
    assert len(provider.generate_prompts) == 0
    assert result.workflow is None


def test_only_success_can_compile_workflow_after_recovery_failure(tmp_path: Path) -> None:
    call = ToolCall("bad", "workspace.search", {"term": "nothing"})
    provider = SequenceProvider(
        [ProviderTurn("", (call,)), ProviderTurn("", (call,)), ProviderTurn("", (call,)), ProviderTurn("", (call,))],
        generated="",
    )

    result = run_agent("search repeatedly", _runtime(tmp_path, provider))

    assert result.status is RunStatus.STALLED
    assert result.workflow is None


def test_malformed_tool_json_executes_only_through_registry_and_permissions(tmp_path: Path) -> None:
    provider = SequenceProvider(
        [ProviderTurn('{"name":"filesystem.write","arguments":{"path":"x.txt","content":"x"}}')]
    )
    runtime = _runtime(tmp_path, provider, answers=("n",))

    result = run_agent("create x.txt containing x", runtime)

    assert result.status is RunStatus.FAILED
    assert not (tmp_path / "x.txt").exists()


def test_unknown_tool_json_is_rejected_without_execution(tmp_path: Path) -> None:
    provider = SequenceProvider([ProviderTurn('{"name":"filesystem.escape","arguments":{"path":"x.txt"}}')])

    result = run_agent("create x.txt", _runtime(tmp_path, provider))

    assert result.status is RunStatus.FAILED
    assert result.tools[0].name == "filesystem.list"


def test_fake_telegram_token_is_not_persisted_or_printed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = "123456789:THIS_IS_A_FAKE_TEST_TOKEN_DO_NOT_USE"
    monkeypatch.setenv("SOVYN_TELEGRAM_TOKEN", fake)
    output = StringIO()

    runtime = boot(StringIO("2\n"), output, interactive=True, workspace=tmp_path)

    assert fake not in output.getvalue()
    assert fake not in runtime.paths.config.read_text(encoding="utf-8")


def _paths(tmp_path: Path):
    from sovyn.paths import default_paths

    paths = default_paths(home=tmp_path / "home", workspace=tmp_path)
    paths.ensure()
    return paths


def _runtime(
    tmp_path: Path,
    provider,
    config=DEFAULT_CONFIG,
    *,
    answers: tuple[str, ...] = ("y",),
) -> AgentRuntime:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(config, Renderer(StringIO(), interactive=False), ScriptedPrompter(answers), trust, True)
    return AgentRuntime(
        provider,
        store,
        interaction.renderer,
        tmp_path,
        interaction,
        workflows_dir=tmp_path / "workflows",
    )
