import json
import re
from pathlib import Path

from sovyn.config import InterfaceLanguage
from sovyn.tool_protocol import ToolCall
from sovyn.tool_registry import ToolValidationError, validate_tool_call
from sovyn.tools import ToolResult

from .language import LANGUAGE_LABELS
from .types import RecoveryAttempt


def parse_text_tool_call(content: str) -> tuple[ToolCall, ...]:
    stripped = content.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return ()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, dict):
        return ()
    if set(payload) - {"id", "name", "arguments"}:
        return ()
    name = payload.get("name")
    arguments = payload.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return ()
    call = ToolCall(str(payload.get("id") or "text-tool"), name, arguments)
    try:
        validate_tool_call(call)
    except ToolValidationError:
        return ()
    return (call,)


def recovery_attempt(
    request: str,
    tools: tuple[ToolResult, ...],
    language: InterfaceLanguage,
    reason: str,
) -> RecoveryAttempt | None:
    relevant = tuple(tool for tool in tools if tool.success and tool.name == "filesystem.read")
    if not relevant:
        return None
    evidence = "\n".join(_compact_evidence(tool) for tool in relevant[-3:])
    prompt = (
        "GOAL:\n"
        f"{request}\n\n"
        "EVIDENCE:\n"
        f"{evidence}\n\n"
        "FAILURE:\n"
        f"{reason}\n\n"
        "ACTION:\n"
        "Return final answer only. Do not call tools.\n"
        f"Language: {LANGUAGE_LABELS[language]}."
    )
    return RecoveryAttempt(prompt, reason)


def exact_write_verified(request: str, workspace: Path, tools: tuple[ToolResult, ...]) -> str | None:
    if not any(tool.success and tool.name == "filesystem.write" for tool in tools):
        return None
    parsed = _parse_exact_write_request(request)
    if parsed is None:
        return None
    path, content = parsed
    target = (workspace / path).resolve()
    try:
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            return f"{path} updated."
    except (PermissionError, UnicodeError, OSError):
        return None
    return None


def _compact_evidence(tool: ToolResult) -> str:
    if tool.name == "filesystem.read":
        return f"- {tool.summary}"
    if tool.name == "filesystem.write":
        status = "no change" if tool.no_change else "written"
        return f"- {Path(tool.output).name}: {status}"
    return f"- {tool.name}: {tool.summary}"


def _parse_exact_write_request(request: str) -> tuple[str, str] | None:
    english = re.search(r"create a file called ([^\s]+) containing (.+)", request, flags=re.IGNORECASE | re.DOTALL)
    if english is not None:
        return english.group(1), english.group(2).strip()
    korean_quoted = re.search(r"([^\s]+\.txt).*?[\"'`](.+?)[\"'`].*?(?:작성|써|만들)", request, flags=re.DOTALL)
    if korean_quoted is not None:
        return korean_quoted.group(1), korean_quoted.group(2).strip()
    korean = re.search(r"([^\s]+\.txt).*?만들고\s+(.+?)\s+(?:라고|이라고|이라는)\s*작성", request, flags=re.DOTALL)
    if korean is not None:
        return korean.group(1), korean.group(2).strip()
    return None
