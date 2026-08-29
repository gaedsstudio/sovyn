import sys

import typer

from sovyn.bench import run_bench
from sovyn.doctor import run_doctor
from sovyn.provider_diagnostics import capability_report
from sovyn.provider_init import ProviderStatus
from sovyn.runtime import boot
from sovyn.ui import DiamondState, Renderer


def register_provider_commands(app: typer.Typer) -> None:
    provider_app = typer.Typer(add_completion=False)
    app.add_typer(provider_app, name="provider")

    @app.command()
    def doctor(providers: bool = typer.Option(False, "--providers")) -> None:
        runtime = boot(sys.stdin, sys.stdout, interactive=False)
        paths = runtime.paths
        renderer = runtime.renderer
        renderer.line(DiamondState.COMPLETED, "SOVYN Doctor")
        for check in run_doctor(paths, runtime.config, runtime.provider):
            state = DiamondState.COMPLETED if check.ok else DiamondState.FAILED
            renderer.line(state, f"{check.name:<18} {check.detail}")
        if providers:
            report = capability_report(runtime.provider)
            renderer.line(DiamondState.COMPLETED, "PROVIDERS")
            renderer.line(DiamondState.WAITING, f"model              {report.model}")
            renderer.line(DiamondState.WAITING, f"tool calling       {report.tool_calling}")
            renderer.line(DiamondState.WAITING, f"streaming          {report.streaming}")
            renderer.line(DiamondState.WAITING, f"context            {report.context}")
            renderer.line(DiamondState.WAITING, f"structured output  {report.structured_output}")

    @provider_app.command("test")
    def provider_test() -> None:
        runtime = boot(sys.stdin, sys.stdout, interactive=False)
        renderer = runtime.renderer
        report = capability_report(runtime.provider)
        renderer.line(DiamondState.COMPLETED, "SOVYN Provider Test")
        renderer.line(DiamondState.WAITING, f"Model {report.model}")
        checks = (
            ("basic response", runtime.provider.status is ProviderStatus.READY),
            ("streaming", report.streaming == "supported"),
            ("tool request", report.tool_calling in {"supported", "probe with sovyn provider test"}),
            ("structured arguments", report.structured_output in {"supported", "model-dependent"}),
            ("tool result followup", runtime.provider.status is ProviderStatus.READY),
        )
        for index, (name, ok) in enumerate(checks, start=1):
            renderer.line(DiamondState.COMPLETED if ok else DiamondState.FAILED, f"{index}  {name:<24} {'PASS' if ok else 'FAIL'}")
        ready = all(ok for _, ok in checks)
        renderer.line(DiamondState.COMPLETED if ready else DiamondState.ATTENTION, "READY" if ready else "COMPATIBILITY UNKNOWN")

    @app.command()
    def bench() -> None:
        run_bench(Renderer(sys.stdout, interactive=False))
