from pathlib import Path
import sys
from dataclasses import dataclass

import typer

from sovyn import __version__
from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import load_config, write_default_config
from sovyn.demo import run_demo
from sovyn.doctor import run_doctor
from sovyn.memory import add_memory, forget_memory, list_memory
from sovyn.paths import default_paths
from sovyn.providers import MockProvider, OllamaProvider, OpenAICompatibleProvider
from sovyn.sessions import list_sessions
from sovyn.storage import Store
from sovyn.ui import DiamondState, Renderer
from sovyn.undo import describe_last_undo
from sovyn.workflows import list_workflows, load_workflow

app = typer.Typer(add_completion=False, no_args_is_help=False, context_settings={"allow_extra_args": True, "ignore_unknown_options": True})

KNOWN_COMMANDS = {"run", "workflows", "sessions", "memory", "config", "doctor", "undo", "demo", "version"}


@dataclass(frozen=True, slots=True)
class OneShotFlags:
    no_interactive: bool
    verbose: bool
    debug: bool


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    no_interactive: bool = typer.Option(False, "--no-interactive"),
    verbose: bool = typer.Option(False, "--verbose"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    paths = default_paths()
    paths.ensure()
    if not paths.config.exists():
        write_default_config(paths.config)
    config = load_config(paths)
    renderer = Renderer(sys.stdout, interactive=False if no_interactive else None)
    if ctx.invoked_subcommand is not None:
        return
    renderer.line(DiamondState.COMPLETED, f"SOVYN {__version__}")
    task = " ".join(ctx.args) if ctx.args else None
    if task is None:
        renderer.line(DiamondState.ATTENTION, f"Model configured: {config.model.provider}/{config.model.model}")
        return
    provider = _provider(config.model.provider, config.model.model)
    result = run_agent(task, AgentRuntime(provider=provider, store=Store(paths.database), renderer=renderer, workspace=paths.workspace))
    if verbose or debug:
        renderer.line(DiamondState.COMPLETED, f"RUN #{result.session_id} {result.duration_seconds:.1f}s")
    typer.echo(result.response)
    if not no_interactive:
        renderer.line(DiamondState.ATTENTION, "This task appears reusable. Create workflow? [Y/n]")


def entrypoint() -> None:
    args = sys.argv[1:]
    first = next((arg for arg in args if not arg.startswith("-")), None)
    if first is None or first in KNOWN_COMMANDS:
        app()
        return
    flags = OneShotFlags(
        no_interactive="--no-interactive" in args,
        verbose="--verbose" in args,
        debug="--debug" in args,
    )
    task = " ".join(arg for arg in args if not arg.startswith("-"))
    _run_one_shot(task, flags)


def _run_one_shot(task: str, flags: OneShotFlags) -> None:
    paths = default_paths()
    paths.ensure()
    if not paths.config.exists():
        write_default_config(paths.config)
    config = load_config(paths)
    renderer = Renderer(sys.stdout, interactive=False if flags.no_interactive else None)
    renderer.line(DiamondState.COMPLETED, f"SOVYN {__version__}")
    provider = _provider(config.model.provider, config.model.model)
    result = run_agent(task, AgentRuntime(provider=provider, store=Store(paths.database), renderer=renderer, workspace=paths.workspace))
    if flags.verbose or flags.debug:
        renderer.line(DiamondState.COMPLETED, f"RUN #{result.session_id} {result.duration_seconds:.1f}s")
    typer.echo(result.response)
    if not flags.no_interactive:
        renderer.line(DiamondState.ATTENTION, "This task appears reusable. Create workflow? [Y/n]")


@app.command()
def run(workflow: str) -> None:
    paths = default_paths()
    loaded = load_workflow(paths.workflows / f"{workflow}.yaml")
    renderer = Renderer(sys.stdout)
    renderer.line(DiamondState.COMPLETED, "Workflow loaded")
    renderer.line(DiamondState.COMPLETED, loaded.name)
    for step in loaded.steps:
        renderer.line(DiamondState.COMPLETED, step.summary)


@app.command()
def workflows() -> None:
    paths = default_paths()
    renderer = Renderer(sys.stdout)
    renderer.line(DiamondState.COMPLETED, "WORKFLOWS")
    for workflow in list_workflows(paths.workflows):
        typer.echo(workflow.name)


@app.command()
def sessions() -> None:
    paths = default_paths()
    for record in list_sessions(Store(paths.database)):
        typer.echo(f"RUN #{record.id} {record.result} {record.tool_calls} tools {record.duration_seconds:.1f}s")


@app.command()
def memory(action: str = "show", note: str | None = None, category: str = "explicitly saved notes") -> None:
    paths = default_paths()
    store = Store(paths.database)
    match action:
        case "show":
            for record in list_memory(store):
                typer.echo(f"{record.id} {record.category}: {record.note}")
        case "add":
            if note is None:
                raise typer.BadParameter("memory add requires a note")
            typer.echo(f"saved {add_memory(store, category, note)}")
        case "forget":
            if note is None:
                raise typer.BadParameter("memory forget requires an id")
            forget_memory(store, int(note))
            typer.echo("forgotten")


@app.command()
def config() -> None:
    paths = default_paths()
    paths.ensure()
    if not paths.config.exists():
        write_default_config(paths.config)
    typer.echo(paths.config)


@app.command()
def doctor() -> None:
    paths = default_paths()
    renderer = Renderer(sys.stdout)
    renderer.line(DiamondState.COMPLETED, "SOVYN Doctor")
    for check in run_doctor(paths):
        state = DiamondState.COMPLETED if check.ok else DiamondState.FAILED
        renderer.line(state, f"{check.name:<18} {check.detail}")


@app.command()
def undo() -> None:
    typer.echo(describe_last_undo(None))


@app.command()
def demo() -> None:
    run_demo(Renderer(sys.stdout, interactive=False))


@app.command("version")
def version_command() -> None:
    typer.echo(__version__)


def _provider(provider: str, model: str):
    match provider:
        case "mock":
            return MockProvider()
        case "ollama":
            return OllamaProvider(model=model)
        case "openai-compatible" | "openai":
            return OpenAICompatibleProvider(model=model, api_key="", base_url="https://api.openai.com/v1", provider_name=provider)
        case _:
            return MockProvider(name=f"mock/{model}")
