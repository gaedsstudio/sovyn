from dataclasses import dataclass
from enum import StrEnum, unique
from typing import NewType

ScenarioId = NewType("ScenarioId", str)


@unique
class TaskName(StrEnum):
    EVENT_EXPLANATION = "event_explanation"
    IMPACT_CLASSIFICATION = "impact_classification"
    TRANSMISSION_CHAIN = "transmission_chain"
    EVIDENCE_FILTERING = "evidence_filtering"
    SUPPORTED_CLAIM = "supported_claim"
    MARKET_BRIEF = "market_brief"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"
    ASK_SOVYN = "ask_sovyn"


@unique
class ImpactDirection(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


@unique
class RelationDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


@unique
class SplitName(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    CHALLENGE = "challenge"


@unique
class ScenarioFamily(StrEnum):
    INFLATION = "inflation"
    EMPLOYMENT = "employment"
    CENTRAL_BANK = "central_bank"
    RATES = "rates"
    FX = "fx"
    EQUITY = "equity"
    COMMODITY = "commodity"
    CRYPTO = "crypto"
    COMPANY = "company"
    COUNTERFACTUAL = "counterfactual"


@dataclass(frozen=True, slots=True)
class Fact:
    metric: str
    actual: float | None
    expected: float | None
    value: float | None
    unit: str
    text: str


@dataclass(frozen=True, slots=True)
class Relationship:
    source: str
    target: str
    direction: RelationDirection
    confidence: float


@dataclass(frozen=True, slots=True)
class Impact:
    target: str
    direction: ImpactDirection
    confidence: float


@dataclass(frozen=True, slots=True)
class Uncertainty:
    level: str
    reason: str


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: ScenarioId
    family: ScenarioFamily
    variant: str
    event_type: str
    date: str
    asset_symbols: tuple[str, ...]
    facts: tuple[Fact, ...]
    relationships: tuple[Relationship, ...]
    impacts: tuple[Impact, ...]
    allowed_claims: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    uncertainty: Uncertainty
    challenge: bool


@dataclass(frozen=True, slots=True)
class DatasetExample:
    example_id: str
    scenario_id: ScenarioId
    scenario_family: ScenarioFamily
    task: TaskName
    instruction: str
    input: str
    output: str
    allowed_claims: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    challenge: bool
