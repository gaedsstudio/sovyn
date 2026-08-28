from io import StringIO
from pathlib import Path

from typer.testing import CliRunner

from sovyn.cli import app
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
    assert "0.1.0" in result.stdout


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
