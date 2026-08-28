# SOVYN Signal ML

The ML workspace prepares parameter-efficient fine-tuning for SOVYN Signal.
It does not train a foundation model and does not download weights during tests.

## Dataset Tasks

- `event_explanation`
- `impact_classification`
- `transmission_chain`
- `evidence_filtering`
- `supported_claim`
- `market_brief`
- `uncertainty_calibration`
- `ask_sovyn`

## Dataset Layout

`ml/datasets/sovyn-v1/` is generated from structured scenarios. Natural-language targets are derived from scenario facts, relationships, allowed claims, forbidden claims, and uncertainty metadata.

Generated artifacts:

- `train.jsonl`
- `validation.jsonl`
- `test.jsonl`
- `challenge.jsonl`
- `review_sample.jsonl`
- `manifest.json`

## Commands

```bash
python -m ml.datasets.generate_v1 --examples 20000 --seed 42
python -m ml.datasets.audit ml/datasets/sovyn-v1
python -m ml.evaluation.benchmark --model mock --dataset ml/datasets/sovyn-v1/test.jsonl
python -m ml.evaluation.compare --base mock --adapter outputs/sovyn-v1-adapter --dataset ml/datasets/sovyn-v1/test.jsonl
python -m ml.training.train --dry-run --method qlora
python -m ml.evaluation.run
python scripts/cleanup_training_artifacts.py
```
