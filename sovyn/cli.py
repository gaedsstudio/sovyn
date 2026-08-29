import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Annotated

import typer

from sovyn import __version__
from sovyn.agent import AgentRuntime, run_agent
from sovyn.bench import run_bench, run_workflow_intelligence_bench
from sovyn.cli_provider import register_provider_commands
from sovyn.config import ModelSettings, load_config, write_config, write_default_config
from sovyn.demo import run_demo
from sovyn.fallback import cloud_context_summary, confirm_fallback, split_model_ref
from sovyn.memory import add_memory, forget_memory, list_memory
from sovyn.paths import default_paths
from sovyn.provider_init import ProviderStatus, resolve_provider
from sovyn.providers import AnthropicProvider, MockProvider, OllamaProvider, OpenAICompatibleProvider
from sovyn.repl import run_repl
from sovyn.runtime import boot
from sovyn.sessions import get_session, list_sessions
from sovyn.storage import Store, trajectory_for_session
from sovyn.stats import render_stats
from sovyn.ui import DiamondState, Renderer
from sovyn.undo import describe_last_undo, restore_last_change
from sovyn.workflows import list_workflows, load_workflow
from sovyn.workflow_runner import run_workflow

app = typer.Typer(add_completion=False, no_args_is_help=False, context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
register_provider_commands(app)

KNOWN_COMMANDS = {"run", "workflow", "workflows", "session", "sessions", "memory", "config", "doctor", "provider", "bench", "undo", "demo", "version"}


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
    task = " ".join(ctx.args) if ctx.args else None
    if task is None:
        run_repl(boot(sys.stdin, sys.stdout, interactive=not no_interactive, debug=debug))
        return
    provider = _provider(config.model.provider, config.model.model, config.model.thinking)
    result = run_agent(
        task,
        AgentRuntime(
            provider=provider,
            store=Store(paths.database),
            renderer=renderer,
            workspace=paths.workspace,
            debug=debug,
            workflows_dir=paths.workflows,
        ),
    )
    if verbose or debug:
        renderer.line(DiamondState.COMPLETED, f"RUN #{result.session_id} {result.duration_seconds:.1f}s")


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
    runtime = boot(sys.stdin, sys.stdout, interactive=not flags.no_interactive, debug=flags.debug)
    paths = runtime.paths
    config = runtime.config
    renderer = runtime.renderer
    renderer.line(DiamondState.COMPLETED, f"SOVYN {__version__}")
    if runtime.provider.status is ProviderStatus.UNAVAILABLE and config.model.provider != "mock":
        fallback_used = False
        if config.model.fallback:
            provider_name, model_name = split_model_ref(config.model.fallback)
            if provider_name and model_name:
                summary = cloud_context_summary(paths.workspace)
                label = f"{provider_name} / {model_name}"
                if confirm_fallback(runtime.interaction, label, summary):
                    fallback = resolve_provider(
                        ModelSettings(provider=provider_name, model=model_name, primary="", fallback="", thinking=False)
                    )
                    if fallback.status is ProviderStatus.READY:
                        runtime = replace(runtime, provider=fallback)
                        fallback_used = True
                    else:
                        renderer.line(DiamondState.FAILED, fallback.detail)
                        return
                else:
                    renderer.line(DiamondState.FAILED, "Provider fallback denied")
                    return
        if not fallback_used:
            _show_provider_unavailable(renderer, runtime.provider.detail)
            return
    result = run_agent(
        task,
        AgentRuntime(
            provider=runtime.provider.provider,
            store=runtime.store,
            renderer=renderer,
            workspace=paths.workspace,
            interaction=runtime.interaction,
            debug=flags.debug,
            workflows_dir=paths.workflows,
        ),
    )
    if flags.verbose or flags.debug:
        renderer.line(DiamondState.COMPLETED, f"RUN #{result.session_id} {result.duration_seconds:.1f}s")


@app.command()
def run(workflow: str) -> None:
    runtime = boot(sys.stdin, sys.stdout, interactive=sys.stdout.isatty())
    run_workflow(runtime.paths.workflows / f"{workflow}.yaml", runtime.paths.workspace, runtime.store, runtime.renderer, runtime.interaction)


workflow_app = typer.Typer(add_completion=False)
app.add_typer(workflow_app, name="workflow")


@workflow_app.command("show")
def workflow_show(name: str) -> None:
    paths = default_paths()
    loaded = load_workflow(paths.workflows / f"{name}.yaml")
    typer.echo(f"WORKFLOW\n\n{loaded.name}")
    for index, step in enumerate(loaded.steps, start=1):
        typer.echo(f"{index}  {step.tool}  {step.kind.value}")


@workflow_app.command("edit")
def workflow_edit(name: str) -> None:
    import os
    import subprocess

    paths = default_paths()
    editor = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "vi")
    subprocess.run([editor, str(paths.workflows / f"{name}.yaml")], check=False)


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
    typer.echo("SESSIONS")
    for record in list_sessions(Store(paths.database)):
        typer.echo(f"#{record.id:04d}   {record.request[:28]:<28} {record.result}")


@app.command()
def session(session_id: int) -> None:
    paths = default_paths()
    store = Store(paths.database)
    record = get_session(store, session_id)
    if record is None:
        typer.echo("Session not found")
        return
    typer.echo(f"REQUEST\n\n{record.request}\n")
    typer.echo("ACTIONS")
    for index, tool in enumerate(trajectory_for_session(store, session_id), start=1):
        typer.echo(f"{index:02d} {tool.name} {tool.summary}")
    typer.echo(f"\nRESULT\n\n{record.result}\n\nDuration\n{record.duration_seconds:.1f}s")


@app.command()
def memory(action: str = "show", note: str | None = None, category: str = "explicitly saved notes") -> None:
    paths = default_paths()
    store = Store(paths.database)
    if action == "show":
        for record in list_memory(store):
            typer.echo(f"{record.id} {record.category}: {record.note}")
        return
    if action == "add":
        if note is None:
            raise typer.BadParameter("memory add requires a note")
        typer.echo(f"saved {add_memory(store, category, note)}")
        return
    if action == "forget":
        if note is None:
            raise typer.BadParameter("memory forget requires an id")
        forget_memory(store, int(note))
        typer.echo("forgotten")
        return
    raise typer.BadParameter(f"unknown memory action: {action}")


config_app = typer.Typer(add_completion=False, invoke_without_command=True)
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_main(
    ctx: typer.Context,
    action: Annotated[str | None, typer.Option("--action", help="Deprecated compatibility option.")] = None,
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if action == "select":
        config_select()
        return
    if action not in (None, "show"):
        raise typer.BadParameter(f"unknown config action: {action}")
    config_show()


@config_app.command("show")
def config_show() -> None:
    paths = default_paths()
    paths.ensure()
    if not paths.config.exists():
        write_default_config(paths.config)
    typer.echo(paths.config.read_text(encoding="utf-8"))


@config_app.command("select")
def config_select() -> None:
    runtime = boot(sys.stdin, sys.stdout, interactive=sys.stdout.isatty())
    ollama = resolve_provider(ModelSettings(provider="ollama", model=runtime.config.model.model, thinking=runtime.config.model.thinking))
    if not ollama.models:
        typer.echo("No Ollama models discovered. Start Ollama or edit the config manually.")
        return
    typer.echo("Installed local models")
    for index, model in enumerate(ollama.models, start=1):
        typer.echo(f"{index}. {model}")
    answer = typer.prompt("Select model number", default="1")
    selected = ollama.models[max(0, min(int(answer) - 1, len(ollama.models) - 1))]
    write_config(runtime.paths.config, replace(runtime.config, model=ModelSettings(provider="ollama", model=selected, thinking=runtime.config.model.thinking)))
    typer.echo(f"Selected ollama/{selected}")


@app.command()
def undo() -> None:
    paths = default_paths()
    restored = restore_last_change(Store(paths.database), paths.workspace)
    if not restored:
        typer.echo(describe_last_undo(Store(paths.database)))
        return
    typer.echo("Reverted last SOVYN change")
    for path in restored:
        typer.echo(path.name)


@app.command()
def stats() -> None:
    paths = default_paths()
    typer.echo(render_stats(Store(paths.database)))


@app.command()
def bench() -> None:
    renderer = Renderer(sys.stdout, interactive=False)
    run_bench(renderer)
    run_workflow_intelligence_bench(renderer)


@app.command()
def demo() -> None:
    run_demo(Renderer(sys.stdout, interactive=False))


@app.command("version")
def version_command() -> None:
    typer.echo(__version__)


def _provider(provider: str, model: str, thinking: bool):
    if provider == "mock":
        return MockProvider()
    if provider == "ollama":
        return OllamaProvider(model=model, thinking=thinking)
    if provider in {"openai-compatible", "openai"}:
        return OpenAICompatibleProvider(model=model, api_key="", base_url="https://api.openai.com/v1", provider_name=provider)
    if provider == "anthropic":
        return AnthropicProvider(model=model, api_key="")
    return MockProvider(name=f"mock/{model}")


def _show_provider_unavailable(renderer: Renderer, detail: str) -> None:
    renderer.line(DiamondState.FAILED, "Ollama unavailable")
    renderer.line(DiamondState.WAITING, detail)
    renderer.line(DiamondState.WAITING, "Options:")
    renderer.line(DiamondState.WAITING, "1. Install Ollama")
    renderer.line(DiamondState.WAITING, "2. Configure OpenAI")
    renderer.line(DiamondState.WAITING, "3. Configure Anthropic")
    renderer.line(DiamondState.WAITING, "4. Configure an OpenAI-compatible endpoint")
