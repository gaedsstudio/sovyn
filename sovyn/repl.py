from sovyn.agent import AgentRuntime, run_agent
from sovyn.commands import SlashCommand, parse_slash_command
from sovyn.provider_init import ProviderStatus
from sovyn.runtime import AppRuntime, show_provider_status
from sovyn.stats import render_stats
from sovyn.tool_registry import tool_schemas
from sovyn.ui import DiamondState
from sovyn.undo import describe_history, describe_last_undo, restore_last_change
from sovyn.workflows import list_workflows


def render_help() -> str:
    return "\n".join(
        (
            "SOVYN commands",
            "/help          show commands",
            "/model         show active model",
            "/status        show task and access state",
            "/tools         list local tools",
            "/permissions   show trust policy",
            "/history       show recent SOVYN changes",
            "/undo          revert last SOVYN change",
            "/workflows     list reusable workflows",
            "/stats         show local reuse stats",
            "/debug         toggle debug output",
            "/clear         clear the screen",
            "/exit          close SOVYN",
        )
    )


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
        command = parse_slash_command(task)
        if command is SlashCommand.EXIT:
            runtime.renderer.line(DiamondState.COMPLETED, "Session closed")
            return
        if command is not None and _handle_command(command, runtime):
            continue
        try:
            result = run_agent(
                task,
                AgentRuntime(
                    provider=runtime.provider.provider,
                    store=runtime.store,
                    renderer=runtime.renderer,
                    workspace=runtime.paths.workspace,
                    interaction=runtime.interaction,
                    debug=runtime.debug,
                    workflows_dir=runtime.paths.workflows,
                ),
            )
        except KeyboardInterrupt:
            runtime.renderer.line(DiamondState.ATTENTION, "Operation cancelled")
            continue


def _handle_command(command: SlashCommand, runtime: AppRuntime) -> bool:
    match command:
        case SlashCommand.HELP:
            runtime.renderer.stream_text(render_help())
            return True
        case SlashCommand.MODEL:
            runtime.renderer.stream_text(runtime.provider.provider.name)
            return True
        case SlashCommand.STATUS:
            runtime.renderer.stream_text(_status(runtime))
            return True
        case SlashCommand.TOOLS:
            runtime.renderer.stream_text("\n".join(schema.name for schema in tool_schemas()))
            return True
        case SlashCommand.PERMISSIONS:
            runtime.renderer.stream_text(_permissions(runtime))
            return True
        case SlashCommand.HISTORY:
            runtime.renderer.stream_text(describe_history(runtime.store))
            return True
        case SlashCommand.UNDO:
            restored = restore_last_change(runtime.store, runtime.paths.workspace)
            if restored:
                runtime.renderer.line(DiamondState.COMPLETED, "Reverted last SOVYN change")
                for path in restored:
                    runtime.renderer.stream_text(path.name)
            else:
                runtime.renderer.stream_text(describe_last_undo(runtime.store))
            return True
        case SlashCommand.WORKFLOWS:
            workflows = list_workflows(runtime.paths.workflows)
            if not workflows:
                runtime.renderer.stream_text("No workflows saved.")
                return True
            runtime.renderer.stream_text("\n".join(workflow.name for workflow in workflows))
            return True
        case SlashCommand.DEBUG:
            runtime.renderer.line(DiamondState.COMPLETED, "Debug output is set at startup with --debug")
            return True
        case SlashCommand.CLEAR:
            runtime.renderer.stream_text("\x1bc")
            return True
        case SlashCommand.STATS:
            runtime.renderer.stream_text(render_stats(runtime.store))
            return True
        case SlashCommand.EXIT:
            runtime.renderer.line(DiamondState.COMPLETED, "Session closed")
            return True


def _status(runtime: AppRuntime) -> str:
    trusted = "granted" if runtime.interaction.trust.is_trusted(runtime.paths.workspace) else "not granted"
    return "\n".join(("Task", "Idle", "", "Permissions", f"READ   {trusted}", "WRITE  ask", "", "Model", runtime.provider.provider.name))


def _permissions(runtime: AppRuntime) -> str:
    permissions = runtime.config.permissions
    return "\n".join(
        (
            "Permissions",
            f"READ FILES    {permissions.read_files.value}",
            f"WRITE FILES   {permissions.write_files.value}",
            f"SHELL         {permissions.shell.value}",
            f"NETWORK       {permissions.network_read.value}",
            f"DELETE        {permissions.delete_files.value}",
            f"GIT COMMIT    {permissions.git_commit.value}",
        )
    )
