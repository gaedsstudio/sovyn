from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
from typing import TypeAlias
from uuid import uuid4

JsonValue: TypeAlias = str | int | float | bool | None | Mapping[str, "JsonValue"] | tuple["JsonValue", ...]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    tool_call_id: str
    success: bool
    output: str
    error: str = ""


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderTurn:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage = TokenUsage()


class CompatibilityParseError(RuntimeError):
    pass


TOOL_BLOCK = re.compile(r"<tool>\s*(.*?)\s*</tool>", flags=re.DOTALL)


def parse_compatibility_tool_calls(text: str) -> tuple[ToolCall, ...]:
    calls: list[ToolCall] = []
    for match in TOOL_BLOCK.finditer(text):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise CompatibilityParseError("Tool block is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise CompatibilityParseError("Tool block must be a JSON object")
        name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not isinstance(name, str):
            raise CompatibilityParseError("Tool name must be a string")
        if not isinstance(arguments, dict):
            raise CompatibilityParseError("Tool arguments must be an object")
        calls.append(ToolCall(str(payload.get("id") or uuid4()), name, arguments))
    return tuple(calls)
