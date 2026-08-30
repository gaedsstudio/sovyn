from dataclasses import dataclass
from enum import StrEnum, unique

from sovyn.config import InterfaceLanguage


@unique
class CapabilityLevel(StrEnum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ModelCapabilityProfile:
    multilingual: CapabilityLevel = CapabilityLevel.UNKNOWN
    tool_calling: CapabilityLevel = CapabilityLevel.UNKNOWN
    completion: CapabilityLevel = CapabilityLevel.UNKNOWN


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    original: str
    prompt: str
    language: InterfaceLanguage


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    prompt: str
    reason: str
