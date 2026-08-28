from pathlib import Path

from sovyn.config import DEFAULT_CONFIG
from sovyn.permissions import ActionKind, PermissionDecision, PermissionRequest, decide_permission
from sovyn.tools import list_files
from sovyn.workflows import StepKind, Workflow, WorkflowStep, load_workflow, save_workflow, workflow_from_success


def test_permission_blocks_ask_policy_when_non_interactive() -> None:
    request = PermissionRequest(ActionKind.WRITE_FILES, "modify files")

    decision = decide_permission(DEFAULT_CONFIG.permissions, request, interactive=False)

    assert decision is PermissionDecision.BLOCK


def test_permission_allows_safe_read_when_policy_allows() -> None:
    request = PermissionRequest(ActionKind.READ_FILES, "read files")

    decision = decide_permission(DEFAULT_CONFIG.permissions, request, interactive=False)

    assert decision is PermissionDecision.ALLOW


def test_workflow_serializes_readable_yaml_when_saved(tmp_path: Path) -> None:
    workflow = Workflow(
        name="repo-check",
        description="Check repo",
        steps=(WorkflowStep("git.status", StepKind.DETERMINISTIC, "Read Git status"),),
    )
    path = tmp_path / "repo-check.yaml"

    save_workflow(path, workflow)
    loaded = load_workflow(path)

    assert loaded.name == "repo-check"
    assert loaded.steps[0].kind is StepKind.DETERMINISTIC


def test_workflow_from_success_records_deterministic_steps() -> None:
    workflow = workflow_from_success("cleanup", "organize downloads", ("filesystem.list", "filesystem.move"))

    assert workflow.name == "cleanup"
    assert tuple(step.kind for step in workflow.steps) == (StepKind.DETERMINISTIC, StepKind.DETERMINISTIC)


def test_workspace_index_ignores_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "sovyn").mkdir()
    (tmp_path / "sovyn" / "cli.py").write_text("", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.js").write_text("", encoding="utf-8")

    result = list_files(tmp_path)

    assert result.summary == "1 files indexed"
