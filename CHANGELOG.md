# Changelog

## 0.1.0a2

- Added Ollama `think` control with `thinking = false` as the default model setting.
- Added debug-only model/tool/total latency timing.
- Added read-only tool-call deduplication with cache invalidation after workspace mutation.
- Changed workflow creation to explicit opt-in and added workflow filename safety validation.
- Added `sovyn config show`, `sovyn config select`, and `python -m sovyn` entrypoints.
- Updated docs to reflect verified Windows + Python 3.14 + Ollama + qwen3:8b E2E coverage.

## 0.1.0a1

- Added canonical provider tool-call and tool-result protocol.
- Added centralized tool schemas, argument validation, path safety, shell danger detection, network read permission prompts, and loop protection.
- Added native tool-call normalization paths for Ollama, OpenAI-compatible providers, and Anthropic, plus strict compatibility-mode parsing.
- Added provider diagnostics through `sovyn doctor --providers` and `sovyn provider test`.
- Added deterministic `sovyn bench` for local agent/workflow regression checks.
- Marked provider tool calling, compatibility mode, agent planning, and workflow learning as experimental alpha features.

## 0.1.0

- Rebooted SOVYN as a terminal-native open-source agent.
- Added local configuration, SQLite storage, provider interfaces, permissions, workflows, memory, sessions, doctor, undo metadata, and diamond terminal rendering.
