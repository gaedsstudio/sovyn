from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from sovyn.agent import AgentRuntime, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.loop_guard import LoopGuard
from sovyn.path_safety import PathSafetyError, resolve_workspace_path
from sovyn.providers import MockProvider
from sovyn.storage import Store
from sovyn.tool_protocol import ToolCall
from sovyn.tool_registry import ToolValidationError, execute_validated_tool, validate_tool_call
from sovyn.trust import WorkspaceTrust
from sovyn.ui import DiamondState, Renderer
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import StepKind, Workflow, WorkflowStep, save_workflow, workflow_path


@dataclass(frozen=True, slots=True)
class BenchCase:
    name: str
    passed: bool


@dataclass(frozen=True, slots=True)
class CompetitiveBenchResult:
    run1_model_calls: int
    run2_model_calls: int
    run3_model_calls: int
    run4_model_calls: int


def run_bench(renderer: Renderer) -> tuple[BenchCase, ...]:
    with TemporaryDirectory(prefix="sovyn-bench-", ignore_cleanup_errors=True) as raw:
        workspace = Path(raw)
        (workspace / "README.md").write_text("# SOVYN\n", encoding="utf-8")
        store = Store(workspace / ".sovyn" / "sovyn.db")
        trust = WorkspaceTrust(store)
        trust.trust(workspace)
        interaction = Interaction(DEFAULT_CONFIG, renderer, _AllowPrompter(), trust, True)
        runtime = AgentRuntime(MockProvider(), store, renderer, workspace, interaction)
        result = run_agent("create a file called hello.txt containing hello", runtime)
        modified = execute_validated_tool(
            validate_tool_call(ToolCall("bench-modify", "filesystem.write", {"path": "notes.txt", "content": "updated"})),
            workspace,
            interaction,
        )
        search = execute_validated_tool(
            validate_tool_call(ToolCall("bench-search", "workspace.search", {"term": "hello"})),
            workspace,
            interaction,
        )
        shell = execute_validated_tool(
            validate_tool_call(ToolCall("bench-shell", "shell.run", {"command": "python --version"})),
            workspace,
            interaction,
        )
        git_status = execute_validated_tool(validate_tool_call(ToolCall("bench-git", "git.status", {})), workspace, interaction)
        workflow_path = workspace / ".sovyn" / "workflows" / "hello.yaml"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        if result.workflow is not None:
            save_workflow(workflow_path, result.workflow)
        replay = run_workflow(workflow_path, workspace, store, renderer, interaction) if workflow_path.exists() else None
        cases = (
            BenchCase("Workspace read", result.tools[0].name == "filesystem.list"),
            BenchCase("File write", (workspace / "hello.txt").exists()),
            BenchCase("File modify", modified.success and (workspace / "notes.txt").read_text(encoding="utf-8") == "updated"),
            BenchCase("Workspace search", search.success and "filename matches" in search.summary),
            BenchCase("Safe shell", shell.success),
            BenchCase("Git status", git_status.success),
            BenchCase("Tool correction", _invalid_args_rejected()),
            BenchCase("Path isolation", _path_escape_rejected(workspace)),
            BenchCase("Loop protection", _loop_rejected()),
            BenchCase("Workflow replay", replay is not None and replay.tool_calls == 1),
        )
    renderer.line(DiamondState.COMPLETED, "SOVYN Agent Bench")
    for case in cases:
        renderer.line(DiamondState.COMPLETED if case.passed else DiamondState.FAILED, f"{case.name:<18} {'PASS' if case.passed else 'FAIL'}")
    renderer.line(DiamondState.COMPLETED, f"{sum(1 for case in cases if case.passed)} / {len(cases)}")
    if replay is not None:
        renderer.line(DiamondState.WAITING, f"First run model calls   {result.model_calls}")
        renderer.line(DiamondState.WAITING, f"Reused run model calls  {replay.model_calls}")
        renderer.line(DiamondState.WAITING, f"First run tool calls    {len(result.tools)}")
        renderer.line(DiamondState.WAITING, f"Reused run tool calls   {replay.tool_calls}")
    return cases


def run_workflow_intelligence_bench(renderer: Renderer) -> CompetitiveBenchResult:
    with TemporaryDirectory(prefix="sovyn-workflow-bench-", ignore_cleanup_errors=True) as raw:
        workspace = Path(raw)
        (workspace / "pyproject.toml").write_text("[project]\nname='bench'\n", encoding="utf-8")
        store = Store(workspace / ".sovyn" / "sovyn.db")
        trust = WorkspaceTrust(store)
        trust.trust(workspace)
        interaction = Interaction(DEFAULT_CONFIG, renderer, _AllowPrompter(), trust, True)
        workflow = Workflow(
            name="python-test-repair",
            description="run tests and fix failures",
            steps=(WorkflowStep("shell.run", StepKind.DETERMINISTIC, "Run tests", "pytest-missing-runner"),),
            project_types=("python",),
        )
        workflows_dir = workspace / ".sovyn" / "workflows"
        save_workflow(workflow_path(workflows_dir, workflow.name), workflow)
        run1 = run_agent("run tests and fix the failure", AgentRuntime(MockProvider(), store, renderer, workspace, interaction))
        run2 = run_workflow(workflow_path(workflows_dir, workflow.name), workspace, store, renderer, interaction)
        (workspace / "uv.lock").write_text("", encoding="utf-8")
        run3 = run_workflow(
            workflow_path(workflows_dir, workflow.name),
            workspace,
            store,
            renderer,
            interaction,
            allow_repair=True,
        )
        run4 = run_workflow(workflow_path(workflows_dir, "python-test-repair-v2"), workspace, store, renderer, interaction)
    result = CompetitiveBenchResult(run1.model_calls, run2.model_calls, run3.model_calls, run4.model_calls)
    renderer.line(DiamondState.COMPLETED, "SOVYN Workflow Intelligence Bench")
    renderer.line(DiamondState.WAITING, f"Run 1 model calls  {result.run1_model_calls}")
    renderer.line(DiamondState.WAITING, f"Run 2 model calls  {result.run2_model_calls}")
    renderer.line(DiamondState.WAITING, f"Run 3 model calls  {result.run3_model_calls}")
    renderer.line(DiamondState.WAITING, f"Run 4 model calls  {result.run4_model_calls}")
    return result


@dataclass(frozen=True, slots=True)
class _AllowPrompter:
    def ask(self, prompt: str) -> str:
        return "y"


def _invalid_args_rejected() -> bool:
    try:
        validate_tool_call(ToolCall("bench-invalid", "filesystem.write", {"content": "missing path"}))
    except ToolValidationError:
        return True
    return False


def _path_escape_rejected(workspace: Path) -> bool:
    try:
        resolve_workspace_path(workspace, "../outside.txt")
    except PathSafetyError:
        return True
    return False


def _loop_rejected() -> bool:
    guard = LoopGuard(limit=3)
    return (
        guard.observe("filesystem.read", '{"path":"README.md"}') is None
        and guard.observe("filesystem.read", '{"path":"README.md"}') is None
        and guard.observe("filesystem.read", '{"path":"README.md"}') is not None
    )
