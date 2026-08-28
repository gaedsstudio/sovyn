from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

from sovyn.config import ModelSettings, SovynConfig, load_config, write_config, write_default_config
from sovyn.interaction import ConsolePrompter, Interaction
from sovyn.paths import SovynPaths, default_paths
from sovyn.provider_init import ProviderResolution, ProviderStatus, resolve_provider
from sovyn.storage import Store
from sovyn.trust import WorkspaceTrust
from sovyn.ui import DiamondState, Renderer


@dataclass(frozen=True, slots=True)
class AppRuntime:
    paths: SovynPaths
    config: SovynConfig
    provider: ProviderResolution
    renderer: Renderer
    interaction: Interaction
    store: Store


def boot(
    input_stream: TextIO,
    output_stream: TextIO,
    interactive: bool,
    workspace: Path | None = None,
) -> AppRuntime:
    paths = default_paths(workspace=workspace)
    paths.ensure()
    if not paths.config.exists():
        write_default_config(paths.config)
    config = load_config(paths)
    renderer = Renderer(output_stream, interactive=interactive)
    provider = resolve_provider(config.model)
    if provider.status is ProviderStatus.UNAVAILABLE and config.model.provider == "ollama" and provider.models:
        config = replace(config, model=ModelSettings(provider="ollama", model=provider.models[0]))
        write_config(paths.config, config)
        provider = resolve_provider(config.model)
    store = Store(paths.database)
    interaction = Interaction(config, renderer, ConsolePrompter(input_stream, output_stream), WorkspaceTrust(store), interactive)
    return AppRuntime(paths, config, provider, renderer, interaction, store)


def show_provider_status(runtime: AppRuntime) -> None:
    runtime.renderer.line(DiamondState.COMPLETED, f"SOVYN 0.1")
    runtime.renderer.line(DiamondState.WAITING, f"model      {runtime.provider.provider.name}")
    runtime.renderer.line(DiamondState.WAITING, f"workspace  {runtime.paths.workspace}")
    if runtime.provider.status is ProviderStatus.UNAVAILABLE:
        runtime.renderer.line(DiamondState.ATTENTION, runtime.provider.detail)
