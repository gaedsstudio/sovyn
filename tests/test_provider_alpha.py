from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG, ModelSettings
from sovyn.fallback import cloud_context_summary, confirm_fallback
from sovyn.interaction import Approval, Interaction, Prompter
from sovyn.loop_guard import LoopGuard
from sovyn.path_safety import PathSafetyError, resolve_workspace_path
from sovyn.provider_init import resolve_provider
from sovyn.providers import AnthropicProvider, MockProvider, OpenAICompatibleProvider, OllamaProvider, ProviderError, ProviderErrorKind, normalize_provider_error
from sovyn.shell_safety import assess_shell_command
from sovyn.storage import Store
from sovyn.tool_protocol import CompatibilityParseError, ToolCall, parse_compatibility_tool_calls
from sovyn.tool_registry import ToolValidationError, execute_validated_tool, validate_tool_call
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(frozen=True, slots=True)
class ScriptedPrompter:
    answers: tuple[str, ...]

    def ask(self, prompt: str) -> str:
        return self.answers[0]


@dataclass(frozen=True, slots=True)
class GenerateResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"response": "done"}


@dataclass(slots=True)  # noqa: MUTABLE_OK
class GenerateClient:
    payloads: list[dict]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        self.payloads.append(json)
        return GenerateResponse()


def test_provider_tool_call_normalizes_compatibility_protocol() -> None:
    calls = parse_compatibility_tool_calls('<tool>{"name":"filesystem.read","arguments":{"path":"README.md"}}</tool>')

    assert calls[0].name == "filesystem.read"
    assert calls[0].arguments == {"path": "README.md"}


def test_provider_tool_call_rejects_invalid_json() -> None:
    with pytest.raises(CompatibilityParseError):
        parse_compatibility_tool_calls("<tool>{bad json}</tool>")


def test_tool_schema_validation_blocks_missing_argument() -> None:
    call = parse_compatibility_tool_calls('<tool>{"name":"filesystem.write","arguments":{"content":"hello"}}</tool>')[0]

    with pytest.raises(ToolValidationError):
        validate_tool_call(call)


def test_path_safety_blocks_traversal_and_windows_drive_escape(tmp_path: Path) -> None:
    with pytest.raises(PathSafetyError):
        resolve_workspace_path(tmp_path, "../outside.txt")

    with pytest.raises(PathSafetyError):
        resolve_workspace_path(tmp_path, "C:/Windows/win.ini")

    with pytest.raises(PathSafetyError):
        resolve_workspace_path(tmp_path, "//server/share/file.txt")


def test_shell_safety_flags_destructive_patterns() -> None:
    assessment = assess_shell_command("git reset --hard")

    assert assessment.safe is False
    assert "git reset --hard" in assessment.reason

    recursive_delete = assess_shell_command("Remove-Item -Recurse C:\\Temp\\x")
    assert recursive_delete.safe is False


def test_loop_guard_detects_repeated_and_alternating_actions() -> None:
    repeated = LoopGuard(limit=3)
    assert repeated.observe("filesystem.read", '{"path":"a.py"}') is None
    assert repeated.observe("filesystem.read", '{"path":"a.py"}') is None
    assert repeated.observe("filesystem.read", '{"path":"a.py"}') is not None

    alternating = LoopGuard(limit=5)
    assert alternating.observe("a", "{}") is None
    assert alternating.observe("b", "{}") is None
    assert alternating.observe("a", "{}") is None
    assert alternating.observe("b", "{}") is not None


def test_network_permission_is_required_for_http_get(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(DEFAULT_CONFIG, Renderer(StringIO(), interactive=False), ScriptedPrompter(("n",)), trust, True)
    call = validate_tool_call(parse_compatibility_tool_calls('<tool>{"name":"http.get","arguments":{"url":"https://example.com"}}</tool>')[0])

    result = execute_validated_tool(call, tmp_path, interaction)

    assert result.success is False
    assert result.error == "Network access denied"


def test_provider_error_normalization_maps_rate_limits() -> None:
    error = normalize_provider_error(429, "retry later")

    assert isinstance(error, ProviderError)
    assert error.kind is ProviderErrorKind.RATE_LIMIT


def test_mock_provider_drives_real_tool_loop(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(DEFAULT_CONFIG, Renderer(StringIO(), interactive=False), ScriptedPrompter(("y",)), trust, True)

    result = run_agent(
        "create a file called hello.txt containing hello",
        AgentRuntime(MockProvider(), store, interaction.renderer, tmp_path, interaction),
    )

    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert result.tools[-1].tool_call_id


def test_cloud_fallback_denial_prevents_provider_switch(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(DEFAULT_CONFIG, Renderer(StringIO(), interactive=False), ScriptedPrompter(("n",)), trust, True)

    allowed = confirm_fallback(interaction, "Anthropic / claude-test", cloud_context_summary(tmp_path))

    assert allowed is False


def test_cloud_context_summary_excludes_secret_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# SOVYN\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=secret\n", encoding="utf-8")

    summary = cloud_context_summary(tmp_path)

    assert summary.file_count == 1
    assert ".env" in summary.sensitive_files


def test_debug_mode_reports_model_tool_and_total_timing(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    stream = StringIO()
    interaction = Interaction(DEFAULT_CONFIG, Renderer(stream, interactive=False), ScriptedPrompter(("y",)), trust, True)

    run_agent(
        "create a file called hello.txt containing hello",
        AgentRuntime(MockProvider(), store, interaction.renderer, tmp_path, interaction, debug=True),
    )

    output = stream.getvalue()
    assert "model turn 1" in output
    assert "filesystem.write" in output
    assert "total" in output


async def _capturing_post_json(url, payload, provider, headers=None):
    _capturing_post_json.payloads.append(payload)
    if url.endswith("/api/chat"):
        return {"message": {"content": "done"}}
    return {"choices": [{"message": {"content": "done"}}], "usage": {}}


_capturing_post_json.payloads = []


def test_ollama_chat_turn_sends_think_false_by_default(monkeypatch) -> None:
    _capturing_post_json.payloads.clear()
    monkeypatch.setattr("sovyn.providers.post_json", _capturing_post_json)

    import anyio

    anyio.run(OllamaProvider("qwen3:8b").turn, "hello", ())

    assert _capturing_post_json.payloads[0]["think"] is False


def test_ollama_chat_turn_sends_think_true_when_enabled(monkeypatch) -> None:
    _capturing_post_json.payloads.clear()
    monkeypatch.setattr("sovyn.providers.post_json", _capturing_post_json)

    import anyio

    anyio.run(OllamaProvider("qwen3:8b", thinking=True).turn, "hello", ())

    assert _capturing_post_json.payloads[0]["think"] is True


def test_ollama_generate_sends_think_setting(monkeypatch) -> None:
    payloads: list[dict] = []
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: GenerateClient(payloads))

    import anyio

    assert anyio.run(OllamaProvider("qwen3:8b").generate, "hello") == "done"
    assert anyio.run(OllamaProvider("qwen3:8b", thinking=True).generate, "hello") == "done"

    assert payloads[0]["think"] is False
    assert payloads[1]["think"] is True


def test_openai_and_anthropic_payloads_do_not_send_ollama_think(monkeypatch) -> None:
    _capturing_post_json.payloads.clear()
    monkeypatch.setattr("sovyn.providers.post_json", _capturing_post_json)

    import anyio

    anyio.run(OpenAICompatibleProvider("test", "key", "https://example.test/v1").turn, "hello", ())
    anyio.run(AnthropicProvider("test", "key").turn, "hello", ())

    assert "think" not in _capturing_post_json.payloads[0]
    assert "think" not in _capturing_post_json.payloads[1]


def test_resolve_provider_preserves_ollama_thinking(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda command: "ollama")

    class TagsResponse:
        def json(self) -> dict[str, tuple[dict[str, str], ...]]:
            return {"models": ({"name": "qwen3:8b"},)}

    resolution = resolve_provider(ModelSettings("ollama", "qwen3:8b", thinking=True), lambda url: TagsResponse())

    assert isinstance(resolution.provider, OllamaProvider)
    assert resolution.provider.thinking is True
