# SOVYN

An open-source terminal agent that turns repeated work into reusable workflows.

> Do it once. SOVYN learns the workflow.

## Install

```bash
pip install sovyn
```

## Run

```bash
sovyn
sovyn "organize the files in this folder"
sovyn run <workflow>
```

## Demo

```bash
sovyn demo
```

```text
◇ Inspecting workspace...
◆ 63 source files found
◇ Checking Git...
◆ Git repository detected
◇ Running tests...
◆ 13 passed
! This task could be saved as a workflow. Create workflow? [Y/n]
```

## Why Workflows

SOVYN can capture successful tool sequences as editable reusable workflows. It records tool names, safe arguments, result summaries, and whether a step is deterministic, agent-required, or user-required.

## Local First

SOVYN stores local state in `~/.sovyn/`:

```text
config.toml
sovyn.db
memory/
workflows/
sessions/
logs/
cache/
```

Ollama is the preferred local provider. Bring-your-own-key providers can be configured for OpenAI-compatible APIs and Anthropic.

## Permissions

SOVYN separates safe inspection from actions that need confirmation. Reads, Git status, and diffs are safe. File writes, package installs, commits, network writes, moves, and deletes require approval or fail in non-interactive mode.

## Commands

```bash
sovyn
sovyn "<task>"
sovyn run <workflow>
sovyn workflows
sovyn sessions
sovyn memory
sovyn config
sovyn doctor
sovyn undo
sovyn version
```

## Community

- GitHub: GITHUB_URL
- Documentation: DOCUMENTATION_URL
- Discord: DISCORD_INVITE_URL

## Contributing

See `.github/CONTRIBUTING.md`.
