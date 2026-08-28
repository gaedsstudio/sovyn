from dataclasses import dataclass, replace
from enum import StrEnum, unique
from pathlib import Path
from typing import Protocol, TextIO

from sovyn.config import SovynConfig
from sovyn.diffing import DiffPreview
from sovyn.permissions import PermissionDecision, PermissionRequest, decide_permission
from sovyn.storage import grant_permission, has_permission_grant
from sovyn.trust import WorkspaceTrust
from sovyn.ui import DiamondState, Renderer
from sovyn.workflows import Workflow


@unique
class Approval(StrEnum):
    ONCE = "once"
    ALWAYS = "always"
    DENY = "deny"


class Prompter(Protocol):
    def ask(self, prompt: str) -> str:
        ...


@dataclass(frozen=True, slots=True)
class ConsolePrompter:
    input_stream: TextIO
    output_stream: TextIO

    def ask(self, prompt: str) -> str:
        self.output_stream.write(prompt)
        self.output_stream.flush()
        raw = self.input_stream.readline()
        if raw == "":
            raise EOFError
        return raw.strip()


@dataclass(frozen=True, slots=True)
class Interaction:
    config: SovynConfig
    renderer: Renderer
    prompter: Prompter
    trust: WorkspaceTrust
    interactive: bool

    def ensure_workspace_trusted(self, workspace: Path) -> bool:
        if self.trust.is_trusted(workspace):
            return True
        self.renderer.line(DiamondState.ATTENTION, "This workspace has not been trusted yet.")
        self.renderer.line(DiamondState.WAITING, str(workspace))
        if not self.interactive:
            return False
        answer = self.prompter.ask("Trust this workspace? [y/N] ")
        if answer.lower() not in {"y", "yes"}:
            return False
        self.trust.trust(workspace)
        self.renderer.line(DiamondState.COMPLETED, "Workspace trusted")
        return True

    def approve(self, request: PermissionRequest, diff: DiffPreview | None = None) -> Approval:
        if has_permission_grant(self.trust.store, request.action.value, request.description):
            return Approval.ALWAYS
        decision = decide_permission(self.config.permissions, request, self.interactive)
        match decision:
            case PermissionDecision.ALLOW:
                return Approval.ONCE
            case PermissionDecision.BLOCK:
                return Approval.DENY
            case PermissionDecision.ASK:
                return self._ask_permission(request, diff)

    def offer_workflow(self, workflow: Workflow, workflows_dir: Path) -> bool:
        if not self.interactive:
            return False
        self.renderer.line(DiamondState.ATTENTION, "This task can be reused.")
        if self.prompter.ask("Create workflow? [Y/n] ").lower() == "n":
            return False
        name = self.prompter.ask("Workflow name: ").strip() or workflow.name
        save_path = workflows_dir / f"{name}.yaml"
        from sovyn.workflows import save_workflow

        save_workflow(save_path, replace(workflow, name=name))
        self.renderer.line(DiamondState.COMPLETED, "Workflow saved")
        return True

    def _ask_permission(self, request: PermissionRequest, diff: DiffPreview | None) -> Approval:
        self.renderer.line(DiamondState.ATTENTION, "Permission required")
        self.renderer.line(DiamondState.WAITING, request.description)
        if diff is not None:
            self.renderer.line(DiamondState.WAITING, f"{diff.path}")
            self.renderer.line(DiamondState.WAITING, f"+{diff.additions} -{diff.deletions}")
        if request.destructive:
            answer = self.prompter.ask("Type DELETE to continue: ")
            return Approval.ONCE if answer == "DELETE" else Approval.DENY
        answer = self.prompter.ask("[y] once  [a] always  [n] deny: ").lower()
        if answer == "a":
            grant_permission(self.trust.store, request.action.value, request.description)
            return Approval.ALWAYS
        if answer in {"y", "yes", ""}:
            return Approval.ONCE
        return Approval.DENY
