from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from typing import Protocol

import httpx

from sovyn.provider_wire import (
    ProviderError,
    ProviderErrorKind,
    anthropic_text,
    anthropic_tool,
    normalize_anthropic_calls,
    normalize_ollama_calls,
    normalize_openai_calls,
    normalize_provider_error,
    ollama_tool,
    openai_tool,
    optional_int,
    post_json,
)
from sovyn.tool_protocol import ProviderTurn, TokenUsage, ToolCall, parse_compatibility_tool_calls
from sovyn.tool_registry import ToolSchema


class ModelProvider(Protocol):
    name: str

    async def generate(self, prompt: str) -> str:
        ...

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        ...

    async def turn(self, prompt: str, tools: tuple[ToolSchema, ...]) -> ProviderTurn:
        ...


@dataclass(frozen=True, slots=True)
class MockProvider:
    name: str = "mock/mock-local"

    async def generate(self, prompt: str) -> str:
        request = prompt.splitlines()[0].replace("User request: ", "")
        return f"Done. Mock provider handled: {request}"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def turn(self, prompt: str, tools: tuple[ToolSchema, ...]) -> ProviderTurn:
        if "filesystem.write:" in prompt:
            return ProviderTurn("Done. Mock provider wrote the requested file.", usage=TokenUsage(estimated_cost="LOCAL"))
        if "create a file called " in prompt.lower() and " containing " in prompt.lower():
            request = prompt.splitlines()[0].removeprefix("User request: ")
            before, content = request.split(" containing ", maxsplit=1)
            path = before.rsplit(" ", maxsplit=1)[-1]
            return ProviderTurn(
                "",
                (ToolCall("mock-write", "filesystem.write", {"path": path, "content": content}),),
                TokenUsage(estimated_cost="LOCAL"),
            )
        return ProviderTurn(await self.generate(prompt), usage=TokenUsage(estimated_cost="LOCAL"))


@dataclass(frozen=True, slots=True)
class OllamaProvider:
    model: str
    base_url: str = "http://localhost:11434"
    thinking: bool = False

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "think": self.thinking},
            )
            response.raise_for_status()
            return str(response.json().get("response", ""))

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": True, "think": self.thinking},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    chunk = str(payload.get("response", ""))
                    if chunk:
                        yield chunk

    async def turn(self, prompt: str, tools: tuple[ToolSchema, ...]) -> ProviderTurn:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": self.thinking,
            "tools": [ollama_tool(schema) for schema in tools],
        }
        data = await post_json(f"{self.base_url}/api/chat", payload, self.name)
        message = data.get("message", {})
        native_calls = normalize_ollama_calls(message.get("tool_calls", ()))
        content = str(message.get("content", ""))
        return ProviderTurn(content, native_calls or parse_compatibility_tool_calls(content), TokenUsage(estimated_cost="LOCAL"))


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProvider:
    model: str
    api_key: str
    base_url: str
    provider_name: str = "openai-compatible"

    @property
    def name(self) -> str:
        return f"{self.provider_name}/{self.model}"

    async def generate(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def turn(self, prompt: str, tools: tuple[ToolSchema, ...]) -> ProviderTurn:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [openai_tool(schema) for schema in tools],
        }
        data = await post_json(f"{self.base_url}/chat/completions", payload, self.name, headers)
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})
        return ProviderTurn(
            str(message.get("content") or ""),
            normalize_openai_calls(message.get("tool_calls", ())),
            TokenUsage(optional_int(usage.get("prompt_tokens")), optional_int(usage.get("completion_tokens"))),
        )


@dataclass(frozen=True, slots=True)
class AnthropicProvider:
    model: str
    api_key: str
    base_url: str = "https://api.anthropic.com/v1"

    @property
    def name(self) -> str:
        return f"anthropic/{self.model}"

    async def generate(self, prompt: str) -> str:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": self.model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json().get("content", [])
            return "".join(str(item.get("text", "")) for item in content)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def turn(self, prompt: str, tools: tuple[ToolSchema, ...]) -> ProviderTurn:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [anthropic_tool(schema) for schema in tools],
        }
        data = await post_json(f"{self.base_url}/messages", payload, self.name, headers)
        usage = data.get("usage", {})
        content = data.get("content", ())
        return ProviderTurn(
            anthropic_text(content),
            normalize_anthropic_calls(content),
            TokenUsage(optional_int(usage.get("input_tokens")), optional_int(usage.get("output_tokens"))),
        )
