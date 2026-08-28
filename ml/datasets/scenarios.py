from dataclasses import dataclass
from random import Random
from typing import Final

from ml.datasets.schemas import (
    Fact,
    Impact,
    ImpactDirection,
    RelationDirection,
    Relationship,
    Scenario,
    ScenarioFamily,
    ScenarioId,
    Uncertainty,
)


@dataclass(frozen=True, slots=True)
class ScenarioTemplate:
    variant: str
    family: ScenarioFamily
    event_type: str
    metric: str
    unit: str
    source: str
    target: str
    relation_direction: RelationDirection
    impact_target: str
    impact_direction: ImpactDirection
    base_actual: float
    base_expected: float | None
    asset_symbols: tuple[str, ...]
    forbidden_roots: tuple[str, ...]
    challenge: bool = False


ASSETS: Final[tuple[str, ...]] = ("SPY", "QQQ", "NVDA", "AMD", "BTC", "GOLD", "OIL", "DXY", "USD/KRW", "US2Y", "US10Y")


TEMPLATES: Final[tuple[ScenarioTemplate, ...]] = (
    ScenarioTemplate("inflation_above_expectation", ScenarioFamily.INFLATION, "inflation_release", "CPI_YOY", "%", "inflation_surprise_up", "rate_expectations", RelationDirection.UP, "growth_equities", ImpactDirection.NEGATIVE, 3.4, 3.1, ("US2Y", "QQQ", "DXY"), ("Fed changed policy", "investors panicked")),
    ScenarioTemplate("inflation_below_expectation", ScenarioFamily.INFLATION, "inflation_release", "CPI_YOY", "%", "inflation_surprise_down", "rate_expectations", RelationDirection.DOWN, "growth_equities", ImpactDirection.POSITIVE, 2.8, 3.1, ("US2Y", "QQQ", "DXY"), ("recession is confirmed", "Fed cut rates")),
    ScenarioTemplate("jobs_above_expectation", ScenarioFamily.EMPLOYMENT, "employment_release", "NONFARM_PAYROLLS", "thousand_jobs", "labor_demand_up", "rate_expectations", RelationDirection.UP, "usd", ImpactDirection.POSITIVE, 245, 180, ("US2Y", "DXY", "SPY"), ("inflation caused the move", "Fed hiked today")),
    ScenarioTemplate("jobs_below_expectation", ScenarioFamily.EMPLOYMENT, "employment_release", "NONFARM_PAYROLLS", "thousand_jobs", "labor_demand_down", "growth_expectations", RelationDirection.DOWN, "cyclical_equities", ImpactDirection.NEGATIVE, 95, 170, ("US10Y", "SPY", "DXY"), ("CPI missed", "company earnings caused it")),
    ScenarioTemplate("unemployment_up", ScenarioFamily.EMPLOYMENT, "employment_release", "UNEMPLOYMENT_RATE", "%", "labor_slack_up", "growth_expectations", RelationDirection.DOWN, "usd", ImpactDirection.NEGATIVE, 4.2, 3.9, ("US2Y", "DXY", "SPY"), ("oil caused unemployment",)),
    ScenarioTemplate("unemployment_down", ScenarioFamily.EMPLOYMENT, "employment_release", "UNEMPLOYMENT_RATE", "%", "labor_slack_down", "wage_pressure", RelationDirection.UP, "rates", ImpactDirection.MIXED, 3.7, 3.9, ("US2Y", "QQQ"), ("Fed announced a cut",)),
    ScenarioTemplate("hawkish_fed", ScenarioFamily.CENTRAL_BANK, "central_bank_event", "FED_TONE", "index", "policy_tone_hawkish", "rate_expectations", RelationDirection.UP, "growth_equities", ImpactDirection.NEGATIVE, 0.8, 0.0, ("US2Y", "QQQ", "DXY"), ("CPI released",)),
    ScenarioTemplate("dovish_fed", ScenarioFamily.CENTRAL_BANK, "central_bank_event", "FED_TONE", "index", "policy_tone_dovish", "rate_expectations", RelationDirection.DOWN, "growth_equities", ImpactDirection.POSITIVE, -0.7, 0.0, ("US2Y", "QQQ"), ("jobs collapsed",)),
    ScenarioTemplate("rate_hike", ScenarioFamily.CENTRAL_BANK, "central_bank_event", "FED_FUNDS_CHANGE", "basis_points", "policy_rate_up", "front_end_yields", RelationDirection.UP, "usd", ImpactDirection.POSITIVE, 25, 0, ("US2Y", "DXY"), ("Fed cut rates",)),
    ScenarioTemplate("rate_cut", ScenarioFamily.CENTRAL_BANK, "central_bank_event", "FED_FUNDS_CHANGE", "basis_points", "policy_rate_down", "front_end_yields", RelationDirection.DOWN, "usd", ImpactDirection.NEGATIVE, -25, 0, ("US2Y", "SPY"), ("Fed hiked rates",)),
    ScenarioTemplate("unexpected_hold", ScenarioFamily.CENTRAL_BANK, "central_bank_event", "FED_DECISION_SURPRISE", "basis_points", "policy_surprise_hold", "rate_expectations", RelationDirection.MIXED, "rates", ImpactDirection.MIXED, 0, 25, ("US2Y", "DXY"), ("clear easing cycle started",), True),
    ScenarioTemplate("short_yield_up", ScenarioFamily.RATES, "yield_move", "US2Y_CHANGE", "basis_points", "short_yields_up", "rate_expectations", RelationDirection.UP, "growth_equities", ImpactDirection.NEGATIVE, 11, 0, ("US2Y", "QQQ"), ("CPI caused yields to rise",), True),
    ScenarioTemplate("short_yield_down", ScenarioFamily.RATES, "yield_move", "US2Y_CHANGE", "basis_points", "short_yields_down", "rate_expectations", RelationDirection.DOWN, "growth_equities", ImpactDirection.POSITIVE, -9, 0, ("US2Y", "QQQ"), ("Fed cut rates",), True),
    ScenarioTemplate("long_yield_up", ScenarioFamily.RATES, "yield_move", "US10Y_CHANGE", "basis_points", "long_yields_up", "discount_rates", RelationDirection.UP, "growth_equities", ImpactDirection.NEGATIVE, 12, 0, ("US10Y", "QQQ"), ("inflation came in hot",), True),
    ScenarioTemplate("long_yield_down", ScenarioFamily.RATES, "yield_move", "US10Y_CHANGE", "basis_points", "long_yields_down", "discount_rates", RelationDirection.DOWN, "gold", ImpactDirection.POSITIVE, -10, 0, ("US10Y", "GOLD"), ("recession is certain",), True),
    ScenarioTemplate("curve_steepening", ScenarioFamily.RATES, "yield_move", "CURVE_2S10S_CHANGE", "basis_points", "curve_steepening", "duration_risk", RelationDirection.MIXED, "banks", ImpactDirection.POSITIVE, 14, 0, ("US2Y", "US10Y"), ("Fed pivoted",)),
    ScenarioTemplate("curve_flattening", ScenarioFamily.RATES, "yield_move", "CURVE_2S10S_CHANGE", "basis_points", "curve_flattening", "growth_signal", RelationDirection.NEGATIVE, "cyclical_equities", ImpactDirection.NEGATIVE, -13, 0, ("US2Y", "US10Y"), ("earnings caused it",)),
    ScenarioTemplate("usd_strength", ScenarioFamily.FX, "fx_move", "DXY_CHANGE", "%", "usd_strength", "global_financial_conditions", RelationDirection.UP, "commodities", ImpactDirection.NEGATIVE, 0.8, 0, ("DXY", "GOLD"), ("Fed changed policy",), True),
    ScenarioTemplate("usd_weakness", ScenarioFamily.FX, "fx_move", "DXY_CHANGE", "%", "usd_weakness", "global_financial_conditions", RelationDirection.DOWN, "commodities", ImpactDirection.POSITIVE, -0.7, 0, ("DXY", "GOLD"), ("jobs report caused it",), True),
    ScenarioTemplate("krw_strength", ScenarioFamily.FX, "fx_move", "USD_KRW_CHANGE", "%", "krw_strength", "korea_risk_appetite", RelationDirection.UP, "korea_equities", ImpactDirection.POSITIVE, -0.6, 0, ("USD/KRW", "QQQ"), ("Bank of Korea intervened",)),
    ScenarioTemplate("krw_weakness", ScenarioFamily.FX, "fx_move", "USD_KRW_CHANGE", "%", "krw_weakness", "imported_inflation_pressure", RelationDirection.UP, "korea_equities", ImpactDirection.NEGATIVE, 0.7, 0, ("USD/KRW", "DXY"), ("US CPI caused KRW weakness",), True),
    ScenarioTemplate("broad_equity_selloff", ScenarioFamily.EQUITY, "equity_index_move", "SPY_CHANGE", "%", "risk_appetite_down", "broad_equities", RelationDirection.NEGATIVE, "risk_assets", ImpactDirection.NEGATIVE, -1.3, 0, ("SPY", "QQQ"), ("inflation caused the selloff",), True),
    ScenarioTemplate("broad_equity_rally", ScenarioFamily.EQUITY, "equity_index_move", "SPY_CHANGE", "%", "risk_appetite_up", "broad_equities", RelationDirection.POSITIVE, "risk_assets", ImpactDirection.POSITIVE, 1.2, 0, ("SPY", "QQQ"), ("Fed cut rates",), True),
    ScenarioTemplate("growth_underperformance", ScenarioFamily.EQUITY, "sector_move", "QQQ_SPY_SPREAD", "%", "growth_underperformance", "duration_sensitivity", RelationDirection.NEGATIVE, "growth_equities", ImpactDirection.NEGATIVE, -0.9, 0, ("QQQ", "SPY"), ("yields caused it",), True),
    ScenarioTemplate("value_underperformance", ScenarioFamily.EQUITY, "sector_move", "VALUE_GROWTH_SPREAD", "%", "value_underperformance", "cyclical_risk", RelationDirection.NEGATIVE, "cyclical_equities", ImpactDirection.NEGATIVE, -0.8, 0, ("SPY", "QQQ"), ("oil caused it",), True),
    ScenarioTemplate("semiconductor_selloff", ScenarioFamily.EQUITY, "sector_move", "SOX_CHANGE", "%", "semiconductor_weakness", "growth_equity_sentiment", RelationDirection.NEGATIVE, "semiconductors", ImpactDirection.NEGATIVE, -2.1, 0, ("NVDA", "AMD", "QQQ"), ("Fed caused chip losses",), True),
    ScenarioTemplate("semiconductor_rally", ScenarioFamily.EQUITY, "sector_move", "SOX_CHANGE", "%", "semiconductor_strength", "growth_equity_sentiment", RelationDirection.POSITIVE, "semiconductors", ImpactDirection.POSITIVE, 2.0, 0, ("NVDA", "AMD", "QQQ"), ("CPI caused chip gains",), True),
    ScenarioTemplate("oil_spike", ScenarioFamily.COMMODITY, "commodity_move", "OIL_CHANGE", "%", "oil_price_up", "inflation_expectations", RelationDirection.UP, "airlines", ImpactDirection.NEGATIVE, 3.2, 0, ("OIL", "SPY"), ("employment caused oil",)),
    ScenarioTemplate("oil_drop", ScenarioFamily.COMMODITY, "commodity_move", "OIL_CHANGE", "%", "oil_price_down", "inflation_expectations", RelationDirection.DOWN, "consumer_margins", ImpactDirection.POSITIVE, -2.8, 0, ("OIL", "SPY"), ("Fed caused oil",)),
    ScenarioTemplate("gold_rally", ScenarioFamily.COMMODITY, "commodity_move", "GOLD_CHANGE", "%", "gold_strength", "safe_haven_demand", RelationDirection.UP, "precious_metals", ImpactDirection.POSITIVE, 1.5, 0, ("GOLD", "DXY"), ("inflation caused gold",), True),
    ScenarioTemplate("gold_selloff", ScenarioFamily.COMMODITY, "commodity_move", "GOLD_CHANGE", "%", "gold_weakness", "real_rate_sensitivity", RelationDirection.NEGATIVE, "precious_metals", ImpactDirection.NEGATIVE, -1.4, 0, ("GOLD", "US10Y"), ("Fed hiked today",), True),
    ScenarioTemplate("bitcoin_rally", ScenarioFamily.CRYPTO, "crypto_move", "BTC_CHANGE", "%", "bitcoin_strength", "crypto_risk_appetite", RelationDirection.POSITIVE, "crypto", ImpactDirection.POSITIVE, 4.5, 0, ("BTC", "QQQ"), ("ETF approval occurred",), True),
    ScenarioTemplate("bitcoin_selloff", ScenarioFamily.CRYPTO, "crypto_move", "BTC_CHANGE", "%", "bitcoin_weakness", "crypto_risk_appetite", RelationDirection.NEGATIVE, "crypto", ImpactDirection.NEGATIVE, -4.2, 0, ("BTC", "QQQ"), ("regulator announced a ban",), True),
    ScenarioTemplate("crypto_volatility_spike", ScenarioFamily.CRYPTO, "crypto_move", "BTC_VOL_CHANGE", "%", "crypto_volatility_up", "risk_controls", RelationDirection.UP, "crypto", ImpactDirection.MIXED, 8.0, 0, ("BTC",), ("price direction is certain",)),
    ScenarioTemplate("earnings_beat", ScenarioFamily.COMPANY, "company_move", "EPS_SURPRISE", "%", "earnings_surprise_up", "company_equity", RelationDirection.POSITIVE, "single_stock", ImpactDirection.POSITIVE, 9.0, 0, ("NVDA",), ("macro rates caused the beat",)),
    ScenarioTemplate("earnings_miss", ScenarioFamily.COMPANY, "company_move", "EPS_SURPRISE", "%", "earnings_surprise_down", "company_equity", RelationDirection.NEGATIVE, "single_stock", ImpactDirection.NEGATIVE, -8.0, 0, ("AMD",), ("CPI caused the miss",)),
    ScenarioTemplate("guidance_raise", ScenarioFamily.COMPANY, "company_move", "GUIDANCE_CHANGE", "%", "guidance_up", "future_earnings_expectations", RelationDirection.UP, "single_stock", ImpactDirection.POSITIVE, 6.0, 0, ("NVDA",), ("Fed drove guidance",)),
    ScenarioTemplate("guidance_cut", ScenarioFamily.COMPANY, "company_move", "GUIDANCE_CHANGE", "%", "guidance_down", "future_earnings_expectations", RelationDirection.DOWN, "single_stock", ImpactDirection.NEGATIVE, -6.0, 0, ("AMD",), ("jobs report drove guidance",)),
)


def generate_scenarios(count: int, seed: int) -> tuple[Scenario, ...]:
    rng = Random(seed)
    scenarios: list[Scenario] = []
    for index in range(count):
        template = TEMPLATES[index % len(TEMPLATES)]
        scenarios.append(_instantiate(template, index, rng))
    return tuple(scenarios)


def _instantiate(template: ScenarioTemplate, index: int, rng: Random) -> Scenario:
    actual = round(template.base_actual + rng.uniform(-0.18, 0.18) * abs(template.base_actual or 1), 2)
    expected = None if template.base_expected is None else round(template.base_expected + rng.uniform(-0.05, 0.05) * abs(template.base_expected or 1), 2)
    confidence = round(rng.uniform(0.62, 0.92), 2)
    date = f"2026-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
    fact_text = _fact_text(template, actual, expected)
    facts = (
        Fact(template.metric, actual if expected is not None else None, expected, actual if expected is None else None, template.unit, fact_text),
        Fact(f"{template.asset_symbols[0]}_MOVE", None, None, round(actual / 10, 2), template.unit, f"{template.asset_symbols[0]} moved {round(actual / 10, 2)} {template.unit}."),
    )
    relationships = (
        Relationship(template.source, template.target, template.relation_direction, confidence),
        Relationship(template.target, template.impact_target, _impact_relation(template.impact_direction), max(round(confidence - 0.11, 2), 0.45)),
    )
    allowed = (
        fact_text,
        f"{template.source} can transmit to {template.target}.",
        f"Impact on {template.impact_target} is {template.impact_direction.value} with less than full certainty.",
    )
    forbidden = template.forbidden_roots + ("investors panicked", "this is a trading recommendation")
    is_challenge = template.challenge and index % 2 == 0
    uncertainty = Uncertainty("medium" if is_challenge else "low", "Evidence identifies relationships but not every underlying cause.")
    scenario_id = ScenarioId(f"{template.variant}_{index:05d}")
    return Scenario(scenario_id, template.family, template.variant, template.event_type, date, template.asset_symbols, facts, relationships, (Impact(template.impact_target, template.impact_direction, confidence),), allowed, forbidden, uncertainty, is_challenge)


def _fact_text(template: ScenarioTemplate, actual: float, expected: float | None) -> str:
    if expected is None:
        return f"{template.metric} printed {actual} {template.unit}."
    return f"{template.metric} printed {actual} {template.unit} versus {expected} expected."


def _impact_relation(direction: ImpactDirection) -> RelationDirection:
    match direction:
        case ImpactDirection.POSITIVE:
            return RelationDirection.POSITIVE
        case ImpactDirection.NEGATIVE:
            return RelationDirection.NEGATIVE
        case ImpactDirection.MIXED:
            return RelationDirection.MIXED
        case ImpactDirection.NEUTRAL:
            return RelationDirection.NEUTRAL
