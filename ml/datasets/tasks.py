import json
from dataclasses import asdict
from typing import assert_never

from ml.datasets.schemas import DatasetExample, Impact, Scenario, TaskName
from ml.datasets.style import style_instruction

JSON_TASKS: frozenset[TaskName] = frozenset(
    {
        TaskName.IMPACT_CLASSIFICATION,
        TaskName.TRANSMISSION_CHAIN,
        TaskName.EVIDENCE_FILTERING,
        TaskName.SUPPORTED_CLAIM,
        TaskName.UNCERTAINTY_CALIBRATION,
    }
)


def examples_from_scenario(scenario: Scenario) -> tuple[DatasetExample, ...]:
    return tuple(_build_example(scenario, task) for task in TaskName)


def _build_example(scenario: Scenario, task: TaskName) -> DatasetExample:
    match task:
        case TaskName.EVENT_EXPLANATION:
            instruction = f"Explain the market event using only supplied evidence. {style_instruction()}"
            input_text = _scenario_payload(scenario)
            output = _event_explanation(scenario)
        case TaskName.IMPACT_CLASSIFICATION:
            instruction = "Classify market impact as strict JSON using supplied evidence only."
            input_text = _scenario_payload(scenario)
            output = _impact_json(scenario.impacts)
        case TaskName.TRANSMISSION_CHAIN:
            instruction = "Return the economic transmission chain as strict JSON."
            input_text = _scenario_payload(scenario)
            output = json.dumps([scenario.relationships[0].source, scenario.relationships[0].target, scenario.relationships[1].target])
        case TaskName.EVIDENCE_FILTERING:
            instruction = "Return only facts relevant to the requested explanation as strict JSON."
            input_text = _filtering_payload(scenario)
            output = json.dumps([fact.text for fact in scenario.facts])
        case TaskName.SUPPORTED_CLAIM:
            instruction = "Decide whether the candidate statement is supported by the evidence. Return strict JSON."
            input_text = _claim_payload(scenario)
            output = json.dumps({"supported": False, "reason": "The supplied evidence does not establish that causal claim."})
        case TaskName.MARKET_BRIEF:
            instruction = f"Write a short SOVYN-style market brief from verified events. {style_instruction()}"
            input_text = _brief_payload(scenario)
            output = _market_brief(scenario)
        case TaskName.UNCERTAINTY_CALIBRATION:
            instruction = "Calibrate confidence from ambiguous evidence. Return strict JSON."
            input_text = _scenario_payload(scenario)
            output = json.dumps({"confidence": 0.48, "reason": scenario.uncertainty.reason})
        case TaskName.ASK_SOVYN:
            instruction = f"Answer the user question from structured context only. {style_instruction()}"
            input_text = _ask_payload(scenario)
            output = _ask_answer(scenario)
        case _ as unreachable:
            assert_never(unreachable)
    return DatasetExample(
        example_id=f"{scenario.scenario_id}:{task.value}",
        scenario_id=scenario.scenario_id,
        scenario_family=scenario.family,
        task=task,
        instruction=instruction,
        input=input_text,
        output=output,
        allowed_claims=scenario.allowed_claims,
        forbidden_claims=scenario.forbidden_claims,
        challenge=scenario.challenge,
    )


def _scenario_payload(scenario: Scenario) -> str:
    return json.dumps(
        {
            "scenario_id": scenario.scenario_id,
            "event_type": scenario.event_type,
            "date": scenario.date,
            "assets": scenario.asset_symbols,
            "facts": [asdict(fact) for fact in scenario.facts],
            "relationships": [asdict(relationship) for relationship in scenario.relationships],
            "allowed_claims": scenario.allowed_claims,
            "forbidden_claims": scenario.forbidden_claims,
            "uncertainty": asdict(scenario.uncertainty),
        },
        ensure_ascii=False,
    )


def _filtering_payload(scenario: Scenario) -> str:
    irrelevant = ("CEO interview sentiment was neutral.", "A weather headline was unrelated.", "No confirmed CPI release appeared unless listed in facts.")
    return json.dumps({"request": f"Explain {scenario.variant}.", "facts": tuple(fact.text for fact in scenario.facts) + irrelevant}, ensure_ascii=False)


def _claim_payload(scenario: Scenario) -> str:
    return json.dumps({"evidence": [fact.text for fact in scenario.facts], "candidate_statement": scenario.forbidden_claims[0]}, ensure_ascii=False)


def _brief_payload(scenario: Scenario) -> str:
    return json.dumps({"verified_events": [scenario.variant], "facts": [fact.text for fact in scenario.facts], "impacts": [asdict(impact) for impact in scenario.impacts]}, ensure_ascii=False)


def _ask_payload(scenario: Scenario) -> str:
    return json.dumps({"question": f"What matters in {scenario.variant}?", "context": json.loads(_scenario_payload(scenario))}, ensure_ascii=False)


def _event_explanation(scenario: Scenario) -> str:
    fact = scenario.facts[0].text
    relation = scenario.relationships[0]
    impact = scenario.impacts[0]
    return (
        f"{fact} The supplied evidence supports {relation.source} moving {relation.target} {relation.direction.value}. "
        f"That is consistent with a {impact.direction.value} impact on {impact.target}, with {scenario.uncertainty.level} uncertainty."
    )


def _impact_json(impacts: tuple[Impact, ...]) -> str:
    return json.dumps({impact.target: {"direction": impact.direction.value, "confidence": impact.confidence} for impact in impacts})


def _market_brief(scenario: Scenario) -> str:
    impact = scenario.impacts[0]
    return (
        f"{scenario.facts[0].text} SOVYN classifies the main transmission as {scenario.relationships[0].source} to {scenario.relationships[0].target}. "
        f"The expected market impact is {impact.direction.value} for {impact.target}; unsupported causes are excluded."
    )


def _ask_answer(scenario: Scenario) -> str:
    impact = scenario.impacts[0]
    return (
        f"The key signal is {scenario.facts[0].text} The context supports a {impact.direction.value} read for {impact.target}. "
        "It does not establish an unsupported external cause."
    )
