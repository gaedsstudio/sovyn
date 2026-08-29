from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShellAssessment:
    safe: bool
    reason: str = ""


DANGEROUS_PATTERNS = (
    "rm -rf",
    "remove-item -recurse",
    "git reset --hard",
    "git clean -fd",
    "format ",
    "diskpart",
    "sudo rm",
    "sudo dd",
    "reg save",
    "security dump",
    "credential",
)


def assess_shell_command(command: str) -> ShellAssessment:
    normalized = " ".join(command.lower().split())
    for pattern in DANGEROUS_PATTERNS:
        if pattern in normalized:
            return ShellAssessment(False, f"Command matches dangerous pattern: {pattern}")
    return ShellAssessment(True)
