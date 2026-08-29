from dataclasses import dataclass
from enum import StrEnum, unique
import json
from typing import TypeAlias

import anyio
import httpx

from sovyn.tool_protocol import ToolCall
from sovyn.tool_registry import ToolSchema

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


@unique
class ProviderErrorKind(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    MODEL_NOT_FOUND = "model_not_found"
    CONTEXT_OVERFLOW = "context_overflow"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"


@dataclass(frozen=True, slots=True)
class ProviderError(RuntimeError):
    kind: ProviderErrorKind
    provider: str
    detail: str
    retry_after_seconds: int | None = None

    def __str__(self) -> str:
        return self.detail


def normalize_provider_error(status_code: int, detail: str, provider: str = "provider") -> ProviderError:
    if status_code in {401, 403}:
        return ProviderError(ProviderErrorKind.AUTHENTICATION_ERROR, provider, detail)
    if status_code == 404:
        return ProviderError(ProviderErrorKind.MODEL_NOT_FOUND, provider, detail)
    if status_code == 429:
        return ProviderError(ProviderErrorKind.RATE_LIMIT, provider, detail)
    if status_code == 400:
        return ProviderError(ProviderErrorKind.CONTEXT_OVERFLOW, provider, detail)
    if status_code >= 500:
        return ProviderError(ProviderErrorKind.SERVER_ERROR, provider, detail)
    return ProviderError(ProviderErrorKind.NETWORK_ERROR, provider, detail)


async def post_json(
    url: str,
    payload: JsonObject,
    provider: str,
    headers: dict[str, str] | None = None,
) -> JsonObject:
    last_error: ProviderError | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            last_error = ProviderError(ProviderErrorKind.TIMEOUT, provider, "Provider request timed out")
            if attempt == 2:
                raise last_error from exc
            await anyio.sleep(0.25 * (2**attempt))
            continue
        except httpx.NetworkError as exc:
            last_error = ProviderError(ProviderErrorKind.NETWORK_ERROR, provider, "Provider network error")
            if attempt == 2:
                raise last_error from exc
            await anyio.sleep(0.25 * (2**attempt))
            continue
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            await anyio.sleep(0.25 * (2**attempt))
            continue
        if response.status_code >= 400:
            raise normalize_provider_error(response.status_code, response.text, provider)
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ProviderError(ProviderErrorKind.SERVER_ERROR, provider, "Provider returned a non-object response")
        return parsed
    if last_error is not None:
        raise last_error
    raise ProviderError(ProviderErrorKind.SERVER_ERROR, provider, "Provider retry limit reached")


def ollama_tool(schema: ToolSchema) -> JsonObject:
    return {"type": "function", "function": {"name": schema.name, "description": schema.description, "parameters": schema.json_schema()}}


def openai_tool(schema: ToolSchema) -> JsonObject:
    return ollama_tool(schema)


def anthropic_tool(schema: ToolSchema) -> JsonObject:
    return {"name": schema.name, "description": schema.description, "input_schema": schema.json_schema()}


def normalize_ollama_calls(raw_calls: JsonValue) -> tuple[ToolCall, ...]:
    if not isinstance(raw_calls, list):
        return ()
    calls: list[ToolCall] = []
    for index, raw in enumerate(raw_calls):
        if isinstance(raw, dict):
            function = raw.get("function", {})
            if isinstance(function, dict) and isinstance(function.get("name"), str) and isinstance(function.get("arguments"), dict):
                calls.append(ToolCall(str(raw.get("id") or f"ollama-{index}"), function["name"], function["arguments"]))
    return tuple(calls)


def normalize_openai_calls(raw_calls: JsonValue) -> tuple[ToolCall, ...]:
    if not isinstance(raw_calls, list):
        return ()
    calls: list[ToolCall] = []
    for index, raw in enumerate(raw_calls):
        if isinstance(raw, dict):
            function = raw.get("function", {})
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                raw_arguments = function.get("arguments", "{}")
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                if isinstance(arguments, dict):
                    calls.append(ToolCall(str(raw.get("id") or f"openai-{index}"), function["name"], arguments))
    return tuple(calls)


def normalize_anthropic_calls(content: JsonValue) -> tuple[ToolCall, ...]:
    if not isinstance(content, list):
        return ()
    calls: list[ToolCall] = []
    for index, item in enumerate(content):
        if isinstance(item, dict) and item.get("type") == "tool_use" and isinstance(item.get("name"), str):
            arguments = item.get("input", {})
            if isinstance(arguments, dict):
                calls.append(ToolCall(str(item.get("id") or f"anthropic-{index}"), item["name"], arguments))
    return tuple(calls)


def anthropic_text(content: JsonValue) -> str:
    if not isinstance(content, list):
        return ""
    return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text")


def optional_int(value: JsonValue) -> int | None:
    return value if isinstance(value, int) else None
