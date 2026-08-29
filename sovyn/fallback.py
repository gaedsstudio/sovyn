from dataclasses import dataclass
from pathlib import Path

from sovyn.interaction import Interaction
from sovyn.ui import DiamondState


SENSITIVE_NAMES = {".env", "credentials.json"}


@dataclass(frozen=True, slots=True)
class CloudContextSummary:
    file_count: int
    byte_count: int
    sensitive_files: tuple[str, ...]


def cloud_context_summary(workspace: Path) -> CloudContextSummary:
    files = []
    sensitive = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SENSITIVE_NAMES:
            sensitive.append(path.name)
            continue
        files.append(path)
    return CloudContextSummary(len(files), sum(path.stat().st_size for path in files), tuple(sorted(sensitive)))


def confirm_fallback(interaction: Interaction, fallback_label: str, summary: CloudContextSummary) -> bool:
    if not interaction.interactive:
        return False
    interaction.renderer.line(DiamondState.ATTENTION, "Provider fallback")
    interaction.renderer.line(DiamondState.WAITING, "Local provider failed.")
    interaction.renderer.line(DiamondState.WAITING, f"Fallback: {fallback_label}")
    interaction.renderer.line(DiamondState.WAITING, "Workspace context may be sent to an external service.")
    interaction.renderer.line(DiamondState.WAITING, "Context to send:")
    interaction.renderer.line(DiamondState.WAITING, f"{summary.file_count} files")
    interaction.renderer.line(DiamondState.WAITING, f"{summary.byte_count} bytes")
    if summary.sensitive_files:
        interaction.renderer.line(DiamondState.WAITING, "Sensitive files excluded: " + ", ".join(summary.sensitive_files))
    answer = interaction.prompter.ask("Continue? [y/N] ").lower()
    return answer in {"y", "yes"}


def split_model_ref(value: str) -> tuple[str, str]:
    provider, separator, model = value.partition("/")
    if not separator or not provider or not model:
        return "", ""
    return provider, model
