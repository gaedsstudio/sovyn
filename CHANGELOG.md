# Changelog

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
