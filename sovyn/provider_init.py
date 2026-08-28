from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, unique
import os
import shutil

import httpx

from sovyn.config import ModelSettings
from sovyn.providers import AnthropicProvider, MockProvider, ModelProvider, OllamaProvider, OpenAICompatibleProvider


@unique
class ProviderStatus(StrEnum):
    READY = "ready"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ProviderResolution:
    provider: ModelProvider
    status: ProviderStatus
    detail: str
    models: tuple[str, ...] = ()


def resolve_provider(settings: ModelSettings, http_get: Callable[[str], httpx.Response] | None = None) -> ProviderResolution:
    match settings.provider:
        case "mock":
            return ProviderResolution(MockProvider(), ProviderStatus.READY, "mock provider ready")
        case "ollama":
            return _resolve_ollama(settings.model, http_get)
        case "openai" | "openai-compatible":
            key = os.environ.get("OPENAI_API_KEY", "")
            status = ProviderStatus.READY if key else ProviderStatus.UNAVAILABLE
            return ProviderResolution(
                OpenAICompatibleProvider(settings.model, key, "https://api.openai.com/v1", settings.provider),
                status,
                "API key configured" if key else "OPENAI_API_KEY is not configured",
            )
        case "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            status = ProviderStatus.READY if key else ProviderStatus.UNAVAILABLE
            return ProviderResolution(
                AnthropicProvider(settings.model, key),
                status,
                "API key configured" if key else "ANTHROPIC_API_KEY is not configured",
            )
        case _:
            return ProviderResolution(MockProvider(), ProviderStatus.UNAVAILABLE, f"Unknown provider: {settings.provider}")


def _resolve_ollama(model: str, http_get: Callable[[str], httpx.Response] | None) -> ProviderResolution:
    if shutil.which("ollama") is None:
        return ProviderResolution(OllamaProvider(model), ProviderStatus.UNAVAILABLE, "ollama command not found")
    getter = http_get or httpx.get
    try:
        response = getter("http://localhost:11434/api/tags")
    except httpx.HTTPError:
        return ProviderResolution(OllamaProvider(model), ProviderStatus.UNAVAILABLE, "Ollama is not running")
    models = tuple(str(item.get("name", "")) for item in response.json().get("models", ()) if item.get("name"))
    status = ProviderStatus.READY if model in models else ProviderStatus.UNAVAILABLE
    detail = "model available" if status is ProviderStatus.READY else f"{model} is not installed"
    return ProviderResolution(OllamaProvider(model), status, detail, models)
