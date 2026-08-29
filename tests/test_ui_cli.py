import subprocess
import sys
from io import StringIO
from pathlib import Path

from typer.testing import CliRunner

from sovyn.cli import app, entrypoint
from sovyn.cli import _show_provider_unavailable
from sovyn.provider_init import ProviderStatus, resolve_provider
from sovyn.config import ModelSettings
from sovyn.ui import DiamondState, FRAMES, Renderer


def test_renderer_uses_stable_lines_when_not_interactive() -> None:
    stream = StringIO()
    renderer = Renderer(stream, interactive=False)

    renderer.update(1, "Reading project")
    renderer.complete("Project indexed")

    assert stream.getvalue().splitlines() == ["◈ Reading project", "◆ Project indexed"]


def test_renderer_uses_diamond_frames() -> None:
    assert FRAMES == ("◇", "◈", "◆", "◈")
    assert DiamondState.FAILED.value == "×"


def test_cli_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0a2" in result.stdout


def test_cli_config_show_commands_use_subcommands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    default_result = CliRunner().invoke(app, ["config"])
    show_result = CliRunner().invoke(app, ["config", "show"])

    assert default_result.exit_code == 0
    assert show_result.exit_code == 0
    assert 'thinking = false' in default_result.stdout
    assert default_result.stdout == show_result.stdout


def test_cli_config_select_subcommand_and_legacy_action_reach_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("shutil.which", lambda command: "ollama")

    class TagsResponse:
        def json(self) -> dict[str, tuple[dict[str, str], ...]]:
            return {"models": ({"name": "qwen3:8b"},)}

    monkeypatch.setattr("httpx.get", lambda url: TagsResponse())

    select_result = CliRunner().invoke(app, ["config", "select"], input="1\n")
    legacy_result = CliRunner().invoke(app, ["config", "--action", "select"], input="1\n")

    assert select_result.exit_code == 0
    assert legacy_result.exit_code == 0
    assert "Selected ollama/qwen3:8b" in select_result.stdout
    assert "Selected ollama/qwen3:8b" in legacy_result.stdout


def test_python_module_entrypoint_prints_version() -> None:
    result = subprocess.run([sys.executable, "-m", "sovyn", "version"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "0.1.0a2" in result.stdout


def test_cli_demo_does_not_require_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["demo"])

    assert result.exit_code == 0
    assert "◆ 13 passed" in result.stdout


def test_ollama_resolution_reports_unavailable_without_network(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda command: "ollama")

    def failing_get(url: str):
        import httpx

        raise httpx.ConnectError("offline")

    resolution = resolve_provider(ModelSettings("ollama", "qwen3:8b"), failing_get)

    assert resolution.status is ProviderStatus.UNAVAILABLE


def test_provider_unavailable_message_lists_recovery_options() -> None:
    stream = StringIO()
    renderer = Renderer(stream, interactive=False)

    _show_provider_unavailable(renderer, "ollama command not found")

    assert "Ollama unavailable" in stream.getvalue()
    assert "Configure Anthropic" in stream.getvalue()
