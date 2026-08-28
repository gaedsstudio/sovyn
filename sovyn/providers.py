from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from typing import Protocol

import httpx


class ModelProvider(Protocol):
    name: str

    async def generate(self, prompt: str) -> str:
        ...

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        ...


@dataclass(frozen=True, slots=True)
class MockProvider:
    name: str = "mock/mock-local"

    async def generate(self, prompt: str) -> str:
        request = prompt.splitlines()[0].replace("User request: ", "")
        return f"Done. Mock provider handled: {request}"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)


@dataclass(frozen=True, slots=True)
class OllamaProvider:
    model: str
    base_url: str = "http://localhost:11434"

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "stream": False})
            response.raise_for_status()
            return str(response.json().get("response", ""))

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "stream": True}) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    chunk = str(payload.get("response", ""))
                    if chunk:
                        yield chunk


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
