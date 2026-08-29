from dataclasses import dataclass

from sovyn.provider_init import ProviderResolution, ProviderStatus


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    model: str
    tool_calling: str
    streaming: str
    context: str
    structured_output: str


def capability_report(provider: ProviderResolution) -> CapabilityReport:
    name = provider.provider.name
    if provider.status is not ProviderStatus.READY:
        return CapabilityReport(name, "unavailable", "unavailable", "unknown", "unknown")
    if name.startswith("mock/"):
        return CapabilityReport(name, "supported", "supported", "small", "supported")
    if name.startswith("ollama/"):
        return CapabilityReport(name, "probe with sovyn provider test", "supported", "detected by model", "model-dependent")
    if name.startswith(("openai/", "openai-compatible/", "anthropic/")):
        return CapabilityReport(name, "supported", "supported", "provider-managed", "supported")
    return CapabilityReport(name, "unknown", "unknown", "unknown", "unknown")
