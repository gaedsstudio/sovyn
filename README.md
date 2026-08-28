# SOVYN Signal

Understand what moved and why.

SOVYN Signal is an AI-powered market intelligence system for detecting meaningful changes in market and economic data, ranking those changes by explainable impact, and explaining them from structured evidence.

It is not a trading bot, prediction platform, brokerage tool, Bloomberg clone, or generic chatbot. The core pipeline is:

```text
DATA
CHANGE DETECTION
EVENT
IMPACT GRAPH
SIGNAL
EXPLANATION
```

## Architecture

This is a one-person startup monorepo:

```text
app/                  Next.js App Router pages and API routes
components/           Reusable product UI
lib/market/           Provider interfaces and deterministic demo data
lib/signals/          Zod schemas and signal types
lib/ai/               Explanation model abstraction
engine/               Deterministic signal intelligence pipeline
supabase/migrations/  Supabase-compatible PostgreSQL schema
ml/                   Dataset, training, inference, and evaluation utilities
tests/                TypeScript and Python tests
```

## How To Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000/today`.

## Demo Mode

The app works without external API keys. `MockMarketProvider` serves deterministic observations for:

```text
SPY QQQ NVDA AMD BTC GOLD OIL DXY USD/KRW US2Y US10Y
```

Today, Asset, Watchlist, Ask, and API routes all use the same deterministic signal pipeline.

## Environment

Copy `.env.example` to `.env.local` and fill only the providers you want to enable. Defaults use mock providers.

```bash
MARKET_PROVIDER=mock
AI_PROVIDER=mock
SOVYN_BASE_MODEL=
SOVYN_MODEL_CACHE_DIR=
```

## Database

The initial Supabase-compatible schema is in:

```text
supabase/migrations/0001_signal_schema.sql
```

It defines users, assets, observations, events, event links, impact rules, signals, watchlists, and AI explanations with the required indexes.

## Signal Pipeline

The deterministic engine lives under `engine/`:

1. `detector` computes absolute change, percentage change, volatility, z-score, percentile, and significance.
2. `events` converts significant moves into typed market events.
3. `rules` maps events to affected market groups.
4. `scoring` calculates component impact scores.
5. `pipeline` ranks final signals.

Scores prioritize events. They are not claims of predictive validity or proven causality.

## AI Generation

The web app depends on an `ExplanationModel` interface:

```ts
interface ExplanationModel {
  explain(context: SignalContext): Promise<Explanation>
}
```

Implemented models:

```text
MockExplanationModel
ExternalLLMModel
SovynFineTunedModel
```

LLMs explain supplied context only. They are not the decision engine.

## Fine-Tuning Pipeline

The ML workspace supports storage-safe LoRA/QLoRA readiness:

```bash
python -m ml.datasets.generate
python -m ml.training.train --dry-run --method qlora
python -m ml.evaluation.run
python scripts/cleanup_training_artifacts.py
```

Dataset tasks:

```text
event_explanation
impact_classification
evidence_grounding
```

The training command defaults to adapter output at:

```text
outputs/sovyn-signal-adapter/
```

It does not automatically merge a full model.

## Tests

```bash
npm run test
npm run typecheck
python -m pytest
```

Tests do not require external API keys or multi-GB model downloads.

## Deployment

Deploy the Next.js app as a normal App Router project. Use Supabase for PostgreSQL when persistence is needed. Keep model weights and generated artifacts outside Git; `.gitignore` blocks common model and checkpoint paths.

