from sovyn.agent import AgentRuntime, run_agent
from sovyn.provider_init import ProviderStatus
from sovyn.runtime import AppRuntime, show_provider_status
from sovyn.ui import DiamondState


def run_repl(runtime: AppRuntime) -> None:
    show_provider_status(runtime)
    if runtime.provider.status is ProviderStatus.UNAVAILABLE:
        runtime.renderer.line(DiamondState.ATTENTION, "Run sovyn doctor for setup details.")
    if not runtime.interaction.ensure_workspace_trusted(runtime.paths.workspace):
        runtime.renderer.line(DiamondState.FAILED, "Workspace is not trusted")
        return
    while True:
        try:
            task = runtime.interaction.prompter.ask("> ").strip()
        except EOFError:
            runtime.renderer.line(DiamondState.COMPLETED, "Session closed")
            return
        except KeyboardInterrupt:
            runtime.renderer.line(DiamondState.ATTENTION, "Operation cancelled")
            continue
        if task in {"exit", "quit"}:
            runtime.renderer.line(DiamondState.COMPLETED, "Session closed")
            return
        if not task:
            continue
        try:
            result = run_agent(
                task,
                AgentRuntime(runtime.provider.provider, runtime.store, runtime.renderer, runtime.paths.workspace, runtime.interaction),
            )
        except KeyboardInterrupt:
            runtime.renderer.line(DiamondState.ATTENTION, "Operation cancelled")
            continue
        if result.workflow is not None:
            runtime.interaction.offer_workflow(result.workflow, runtime.paths.workflows)
