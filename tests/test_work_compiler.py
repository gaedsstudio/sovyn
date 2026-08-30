from collections.abc import AsyncIterator
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from sovyn.agent import AgentRuntime, RunStatus, run_agent
from sovyn.config import DEFAULT_CONFIG
from sovyn.interaction import Interaction
from sovyn.permissions import ActionKind
from sovyn.stats import local_stats
from sovyn.storage import Store
from sovyn.tool_protocol import ProviderTurn, ToolCall
from sovyn.tools import ToolResult
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer
from sovyn.work_compiler import SuccessfulRun, compile_successful_run
from sovyn.workflow_runner import run_workflow
from sovyn.workflows import StepKind, Workflow, WorkflowStep, save_workflow, workflow_path


@dataclass(slots=True)  # noqa
class QueuePrompter:
    answers: list[str]
    prompts: list[str]

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@dataclass(slots=True)  # noqa
class FailingProvider:
    calls: int = 0

    @property
    def name(self) -> str:
        return "test/failing"

    async def generate(self, prompt: str) -> str:
        self.calls += 1
        raise AssertionError("provider must not be called")

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.calls += 1
        raise AssertionError("provider must not be called")
        yield ""

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.calls += 1
        raise AssertionError("provider must not be called")


@dataclass(slots=True)  # noqa
class SequenceProvider:
    turns: list[ProviderTurn]
    calls: int = 0

    @property
    def name(self) -> str:
        return "test/sequence"

    async def generate(self, prompt: str) -> str:
        self.calls += 1
        return "done"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def turn(self, prompt: str, tools) -> ProviderTurn:
        self.calls += 1
        if self.turns:
            return self.turns.pop(0)
        return ProviderTurn("done")


def test_compiler_collapses_duplicate_no_op_write_for_deterministic_replay(tmp_path: Path) -> None:
    call = ToolCall("write-1", "filesystem.write", {"path": "output.txt", "content": "Hello from SOVYN"})
    repeated = ToolCall("write-2", "filesystem.write", {"path": "output.txt", "content": "Hello from SOVYN"})
    result = ToolResult("filesystem.write", "wrote output.txt", str(tmp_path / "output.txt"), "write-1")
    no_op = ToolResult(
        "filesystem.write",
        "already up to date",
        str(tmp_path / "output.txt"),
        "write-2",
        no_change=True,
    )

    compiled = compile_successful_run(
        SuccessfulRun("create output.txt containing Hello from SOVYN", (call, repeated), (result, no_op), tmp_path)
    )

    assert compiled.workflow is not None
    assert compiled.deterministic is True
    assert compiled.workflow.model_required is False
    assert compiled.workflow.permissions == (ActionKind.WRITE_FILES.value,)
    assert tuple((step.tool, step.argument, step.content) for step in compiled.workflow.steps) == (
        ("filesystem.write", "output.txt", "Hello from SOVYN"),
    )


def test_compiler_rejects_failed_tool_trajectory(tmp_path: Path) -> None:
    call = ToolCall("write-1", "filesystem.write", {"path": "output.txt", "content": "Hello from SOVYN"})
    failed = ToolResult("filesystem.write", "write failed", tool_call_id="write-1", success=False, error="denied")

    compiled = compile_successful_run(
        SuccessfulRun("create output.txt containing Hello from SOVYN", (call,), (failed,), tmp_path)
    )

    assert compiled.workflow is None
    assert compiled.deterministic is False


def test_compiler_rejects_path_escape(tmp_path: Path) -> None:
    call = ToolCall("write-1", "filesystem.write", {"path": "../escape.txt", "content": "x"})
    result = ToolResult("filesystem.write", "wrote escape.txt", str(tmp_path / "escape.txt"), "write-1")

    compiled = compile_successful_run(SuccessfulRun("create ../escape.txt containing x", (call,), (result,), tmp_path))

    assert compiled.workflow is None
    assert compiled.deterministic is False


def test_compiler_keeps_one_read_but_marks_summary_as_model_required(tmp_path: Path) -> None:
    read = ToolCall("read-1", "filesystem.read", {"path": "README.md"})
    repeated = ToolCall("read-2", "filesystem.read", {"path": "README.md"})
    first = ToolResult("filesystem.read", "10 characters read", "# SOVYN", "read-1")
    cached = ToolResult("filesystem.read", "10 characters read", "# SOVYN", "read-2")

    compiled = compile_successful_run(
        SuccessfulRun("read README.md and summarize it", (read, repeated), (first, cached), tmp_path)
    )

    assert compiled.workflow is not None
    assert compiled.deterministic is False
    assert compiled.workflow.model_required is True
    assert tuple(step.tool for step in compiled.workflow.steps) == ("filesystem.read",)


def test_deterministic_compiled_workflow_replays_without_provider(tmp_path: Path) -> None:
    workflow = Workflow(
        "create-output-txt",
        "Reusable workflow for: create output.txt containing Hello from SOVYN",
        (
            WorkflowStep(
                "filesystem.write",
                StepKind.DETERMINISTIC,
                "Run filesystem.write",
                "output.txt",
                "Hello from SOVYN",
            ),
        ),
        permissions=(ActionKind.WRITE_FILES.value,),
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction = _interaction(tmp_path, ["y", "y"])
    provider = FailingProvider()

    result = run_agent(
        "create output.txt containing Hello from SOVYN",
        AgentRuntime(provider, store, interaction.renderer, tmp_path, interaction, workflows_dir=tmp_path),
    )

    assert provider.calls == 0
    assert result.status is RunStatus.SUCCESS
    assert result.model_calls == 0
    assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "Hello from SOVYN"


def test_non_interactive_success_returns_candidate_without_learning_prompt(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# SOVYN", encoding="utf-8")
    provider = SequenceProvider(
        [
            ProviderTurn("", (ToolCall("read-1", "filesystem.read", {"path": "README.md"}),)),
            ProviderTurn("done"),
        ]
    )
    store, interaction = _interaction(tmp_path)
    interaction = Interaction(DEFAULT_CONFIG, interaction.renderer, QueuePrompter([], []), interaction.trust, False)

    result = run_agent(
        "read README.md",
        AgentRuntime(
            provider,
            store,
            interaction.renderer,
            tmp_path,
            interaction,
            workflows_dir=tmp_path / "workflows",
        ),
    )

    assert result.status is RunStatus.SUCCESS
    assert result.workflow is not None
    assert not (tmp_path / "workflows").exists()


def test_interactive_success_saves_workflow_only_after_learn_acceptance(tmp_path: Path) -> None:
    write = ToolCall("write-1", "filesystem.write", {"path": "output.txt", "content": "Hello from SOVYN"})
    repeated = ToolCall("write-2", "filesystem.write", {"path": "output.txt", "content": "Hello from SOVYN"})
    provider = SequenceProvider([ProviderTurn("", (write,)), ProviderTurn("", (repeated,))])
    store, interaction = _interaction(tmp_path, ["y", "y", "learned-output"])
    interaction = Interaction(
        DEFAULT_CONFIG,
        Renderer(StringIO(), interactive=True),
        interaction.prompter,
        interaction.trust,
        True,
    )

    result = run_agent(
        "create output.txt containing Hello from SOVYN",
        AgentRuntime(
            provider,
            store,
            interaction.renderer,
            tmp_path,
            interaction,
            workflows_dir=tmp_path / "workflows",
        ),
    )

    assert result.status is RunStatus.SUCCESS
    assert (tmp_path / "workflows" / "learned-output.yaml").exists()


def test_model_required_workflow_step_fails_without_fake_success(tmp_path: Path) -> None:
    workflow = Workflow(
        "summarize-readme",
        "Reusable workflow for: read README.md and summarize it",
        (WorkflowStep("filesystem.read", StepKind.MODEL_REQUIRED, "Summarize README", "README.md"),),
        model_required=True,
    )
    save_workflow(workflow_path(tmp_path, workflow.name), workflow)
    store, interaction = _interaction(tmp_path)

    result = run_workflow(
        workflow_path(tmp_path, workflow.name),
        tmp_path,
        store,
        Renderer(StringIO(), interactive=False),
        interaction,
    )

    assert result.status == "failed"
    assert result.model_calls == 0
    assert local_stats(store).zero_model_runs == 0


def _interaction(tmp_path: Path, answers: list[str] | None = None) -> tuple[Store, Interaction]:
    store = Store(tmp_path / "sovyn.db")
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    interaction = Interaction(
        DEFAULT_CONFIG,
        Renderer(StringIO(), interactive=False),
        QueuePrompter(answers or ["y"], []),
        trust,
        True,
    )
    return store, interaction
