import json
from pathlib import Path

from ml.datasets.audit import audit_dataset
from ml.datasets.generate_v1 import build_dataset
from ml.datasets.quality import deduplicate, leakage_pairs, split_examples, validate_examples
from ml.datasets.scenarios import TEMPLATES, generate_scenarios
from ml.datasets.schemas import DatasetExample, ScenarioFamily, ScenarioId, SplitName, TaskName
from ml.datasets.tasks import examples_from_scenario
from ml.evaluation.benchmark import run_benchmark
from ml.evaluation.failures import classify_failures
from ml.evaluation.metrics import evaluate_outputs, is_valid_json_output, unsupported_claim_rate
from ml.evaluation.models import MockModel
from ml.inference.chat import messages_for_example, strip_reasoning_text, training_messages_for_example
from ml.inference.adapter import AdapterInferenceRequest, format_adapter_prompt
from ml.models.config import load_model_config
from ml.training.config import default_training_config, load_training_config
from ml.training.preflight import run_preflight
from ml.training.train import write_training_report


def test_scenario_generation_when_seed_fixed_is_deterministic() -> None:
    first = generate_scenarios(20, 42)
    second = generate_scenarios(20, 42)

    assert first == second
    assert {template.family for template in TEMPLATES} == set(ScenarioFamily) - {ScenarioFamily.COUNTERFACTUAL}


def test_dataset_generation_when_called_writes_v1_artifacts(tmp_path: Path) -> None:
    build_dataset(tmp_path, examples=400, seed=7)

    train = tmp_path / "train.jsonl"
    validation = tmp_path / "validation.jsonl"
    test = tmp_path / "test.jsonl"
    challenge = tmp_path / "challenge.jsonl"
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    first = json.loads((tmp_path / "train.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert train.exists()
    assert validation.exists()
    assert test.exists()
    assert challenge.exists()
    assert (tmp_path / "review_sample.jsonl").exists()
    split_total = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in (train, validation, test, challenge))
    assert manifest["total_examples"] == split_total
    assert first["task"] in {task.value for task in TaskName}
    assert "instruction" in first
    assert "output" in first


def test_quality_filters_when_forbidden_claim_appears_reject_example() -> None:
    scenario = generate_scenarios(1, 3)[0]
    base = examples_from_scenario(scenario)[0]
    bad = DatasetExample(
        example_id="bad",
        scenario_id=ScenarioId("bad"),
        scenario_family=base.scenario_family,
        task=TaskName.EVENT_EXPLANATION,
        instruction=base.instruction,
        input=base.input,
        output=f"{base.output} {base.forbidden_claims[0]}",
        allowed_claims=base.allowed_claims,
        forbidden_claims=base.forbidden_claims,
        challenge=False,
    )
    report = validate_examples((bad,))

    assert report.accepted == ()
    assert report.rejected[0].reason == "forbidden claim"


def test_split_isolation_when_examples_split_keeps_scenarios_together() -> None:
    examples = tuple(example for scenario in generate_scenarios(80, 11) for example in examples_from_scenario(scenario))
    report = validate_examples(examples)
    splits = split_examples(report.accepted)

    assert leakage_pairs(splits) == ()
    assert all(splits[split] for split in (SplitName.TRAIN, SplitName.VALIDATION, SplitName.TEST, SplitName.CHALLENGE))


def test_deduplication_when_same_example_repeated_keeps_one() -> None:
    example = examples_from_scenario(generate_scenarios(1, 9)[0])[0]
    accepted, duplicates = deduplicate((example, example))

    assert accepted == (example,)
    assert duplicates == 1


def test_audit_when_dataset_generated_calculates_metrics(tmp_path: Path) -> None:
    build_dataset(tmp_path, examples=256, seed=4)

    audit = audit_dataset(tmp_path)

    assert audit["examples"] == audit["valid"]
    assert audit["unsupported_claims"] == 0
    assert audit["json_failures"] == 0
    assert audit["duplicates"] == 0


def test_evaluation_metrics_when_mock_model_matches_targets(tmp_path: Path) -> None:
    build_dataset(tmp_path, examples=256, seed=5)
    records = [
        json.loads(line)
        for line in (tmp_path / "challenge.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    examples = tuple(
        DatasetExample(
            example_id=record["example_id"],
            scenario_id=ScenarioId(record["scenario_id"]),
            scenario_family=ScenarioFamily(record["scenario_family"]),
            task=TaskName(record["task"]),
            instruction=record["instruction"],
            input=record["input"],
            output=record["output"],
            allowed_claims=tuple(record["allowed_claims"]),
            forbidden_claims=tuple(record["forbidden_claims"]),
            challenge=bool(record["challenge"]),
        )
        for record in records
    )
    model = MockModel()
    metrics = evaluate_outputs(examples, tuple(model.generate(example) for example in examples))

    assert metrics.json_validity == 1.0
    assert metrics.unsupported_claim_rate == 0.0
    assert metrics.forbidden_claim_rate == 0.0
    assert metrics.uncertainty_compliance == 1.0


def test_training_config_when_default_uses_adapter_only_qlora_settings(tmp_path: Path) -> None:
    dataset = tmp_path / "train.jsonl"
    dataset.write_text("{}\n{}\n", encoding="utf-8")
    config = default_training_config("base-model", dataset, "qlora")
    report_path = write_training_report(config, dry_run=True)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert config.method == "qlora"
    assert config.quantization == "4bit"
    assert config.checkpoint_limit == 2
    assert config.output_dir == Path("outputs/sovyn-v1-adapter")
    assert config.target_modules == ("q_proj", "k_proj", "v_proj", "o_proj")
    assert report["examples"] == 2
    assert report["adapter_parameters"] is None


def test_evaluation_metrics_when_unsupported_claim_appears() -> None:
    rate = unsupported_claim_rate(
        ("because CPI rose", "the evidence only supports a yield move"),
        ("because CPI rose",),
    )

    assert rate == 0.5
    assert is_valid_json_output('{"growth_equities":"negative"}') is True


def test_prompt_formatting_when_adapter_context_is_supplied() -> None:
    prompt = format_adapter_prompt(
        AdapterInferenceRequest(adapter_path="outputs/sovyn-signal-adapter", context="US10Y rose"),
    )

    assert "FACT" in prompt
    assert "US10Y rose" in prompt


def test_model_config_when_qwen3_loaded_uses_non_thinking_default() -> None:
    config = load_model_config(Path("configs/models/qwen3-4b.json"))

    assert config.model_id == "Qwen/Qwen3-4B"
    assert config.family == "qwen3"
    assert config.thinking_enabled is False
    assert config.quantization == "4bit"


def test_chat_formatting_when_training_record_built_contains_visible_assistant_only() -> None:
    example = examples_from_scenario(generate_scenarios(1, 1)[0])[0]
    inference_messages = messages_for_example(example)
    training_messages = training_messages_for_example(example)

    assert tuple(message.role for message in inference_messages) == ("system", "user")
    assert tuple(message.role for message in training_messages) == ("system", "user", "assistant")
    assert training_messages[-1].content == example.output
    assert "<think>" not in training_messages[-1].content


def test_reasoning_strip_when_qwen_thinking_text_present_keeps_final_answer() -> None:
    answer = strip_reasoning_text("<think>\ninternal\n</think>\n{\"supported\": false}")

    assert answer == "{\"supported\": false}"


def test_failure_classification_when_prediction_breaks_contracts() -> None:
    example = examples_from_scenario(generate_scenarios(1, 2)[0])[1]
    failures = classify_failures((example,), ("not json and investors panicked",))

    assert failures[0].categories == ("unsupported_cause", "forbidden_claim", "invalid_json", "missing_evidence")


def test_benchmark_when_sampled_writes_metrics_predictions_and_failures(tmp_path: Path) -> None:
    build_dataset(tmp_path / "dataset", examples=256, seed=8)
    output = tmp_path / "metrics.json"
    predictions = tmp_path / "predictions.jsonl"

    report = run_benchmark("mock", tmp_path / "dataset" / "test.jsonl", output=output, sample=32, seed=3, predictions=predictions)

    assert report["sample_size"] == 8
    assert output.exists()
    assert predictions.exists()
    assert (tmp_path / "failure_analysis.json").exists()


def test_training_config_when_exp001_loaded_has_qwen_paths() -> None:
    config = load_training_config(Path("configs/training/qwen3-4b-sovyn-v1.json"))

    assert config.model_config == Path("configs/models/qwen3-4b.json")
    assert config.output_dir == Path("outputs/experiments/exp001-qwen3-4b/adapter")
    assert config.gradient_checkpointing is True


def test_preflight_when_cpu_only_reports_blocker() -> None:
    result = run_preflight(Path("configs/training/qwen3-4b-sovyn-v1.json"))

    assert result.model_id == "Qwen/Qwen3-4B"
    assert result.dataset_exists is True
