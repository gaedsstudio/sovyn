# SOVYN

**Open-source terminal agent that turns successful work into reusable workflows.**

> Do it once. SOVYN learns the workflow.

[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/gaedsstudio/sovyn/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://github.com/gaedsstudio/sovyn)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/gaedsstudio/sovyn/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/gaedsstudio/sovyn?include_prereleases)](https://github.com/gaedsstudio/sovyn/releases)

SOVYN runs in your terminal, uses local or bring-your-own-key language models, executes tools with explicit permissions, and can capture successful tool sequences as editable workflows.

> [!WARNING]
> SOVYN is alpha software.
> It can execute shell commands and modify files.
> Use it in version-controlled workspaces and review permission prompts carefully.

## Demo

```text
$ sovyn

SOVYN 0.1
model      ollama/qwen3:8b
workspace  ~/project

> create hello.txt containing Hello from SOVYN

! This workspace has not been trusted yet.
Trust this workspace? [y/N] y

! Permission required
Create or modify hello.txt
[y] once  [a] always  [n] deny: y

◆ wrote hello.txt
Done. Mock provider wrote the requested file.

This task can be reused.
Create workflow? [y/N] y
Workflow name: hello-file

◆ Workflow saved

$ sovyn run hello-file
◆ hello.txt created
```

For the recording plan, see [docs/demo-script.txt](https://github.com/gaedsstudio/sovyn/blob/main/docs/demo-script.txt).

## Why SOVYN?

### Local-first

Use Ollama or bring your own API provider. SOVYN does not require a hosted account to run with local models.

### Explicit permissions

SOVYN asks before modifying files, running sensitive commands, or sending workspace context to cloud providers.

### Inspectable

Sessions, memory, workflows, and tool activity remain visible to the user in local state.

### Reusable workflows

Successful tool sequences can become editable workflows and be replayed later.

## Architecture

```text
User
  |
  v
SOVYN Agent Loop -----> Provider
  |                      |-- Ollama
  |                      |-- OpenAI-compatible
  |                      `-- Anthropic
  v
Permissions
  |
  v
Tools
  |-- Filesystem
  |-- Shell
  |-- Git
  |-- HTTP
  `-- Python
  |
  v
Trajectory
  |
  v
Reusable Workflow
```

## Installation

### Public Install

SOVYN is being prepared for public package publication. Until the package is published to PyPI, do not assume `pipx install sovyn` or `pip install sovyn` will work from the public index.

After PyPI publication, the preferred CLI install will be:

```bash
pipx install sovyn
```

### Development Install

```bash
git clone https://github.com/gaedsstudio/sovyn.git
cd sovyn
py -m pip install -e .[dev]
```

On Unix-like systems, replace `py` with `python3` if needed.

## Windows Note

If `sovyn` is installed but the command is not found, the Python `Scripts` directory may not be on `PATH`. Check the location with:

```powershell
py -m site --user-base
```

The executable is usually under that directory's `Scripts` folder. SOVYN does not modify `PATH` automatically. Prefer `pipx` for end-user CLI installation once the package is available.

If `sovyn` is not recognized, you can also run SOVYN through Python:

```powershell
py -m sovyn
py -m sovyn version
py -m sovyn config select
```

## Provider Support

| Provider          | Status                           |   Local |    Tool calling |
| ----------------- | -------------------------------- | ------: | --------------: |
| Mock              | Tested                           |       ✓ |               ✓ |
| Ollama            | Verified on Windows with qwen3:8b |       ✓ | model-dependent |
| OpenAI-compatible | Supported                        | depends |       supported |
| Anthropic         | Supported                        |       ✗ |       supported |

Windows + Python 3.14 + Ollama + `qwen3:8b` has been verified with `sovyn provider test` and a real filesystem read/write task. Linux and macOS real-provider E2E coverage still needs separate validation. Ollama behavior depends on the model's native tool support.

## Commands

```bash
sovyn
sovyn "<task>"
sovyn run <workflow>
sovyn workflows
sovyn sessions
sovyn memory
sovyn config
sovyn config show
sovyn config select
sovyn doctor
sovyn doctor --providers
sovyn provider test
sovyn bench
sovyn undo
sovyn version
```

## Workflow Example

```yaml
name: changelog-from-git
steps:
  - tool: git.log
  - agent:
      task: summarize_commits
  - tool: filesystem.write
    path: CHANGELOG.md
```

Deterministic steps execute directly. Agent-required steps call the configured model. Permissions remain enforced during replay.

## Security

SOVYN can execute code. Its security model relies on workspace isolation, explicit permissions, path validation, dangerous-command detection, network permission prompts, cloud-context confirmation, and bounded agent loops.

SOVYN does not make arbitrary model-generated shell commands safe. Review prompts and run it in version-controlled workspaces.

Read [SECURITY.md](https://github.com/gaedsstudio/sovyn/blob/main/SECURITY.md) before using SOVYN on important files.

## Privacy

SOVYN has no mandatory account, no mandatory cloud, and no mandatory telemetry. Local state is stored under `~/.sovyn`.

You can run with local Ollama models or bring your own provider keys. Cloud model providers may receive selected workspace context only when you configure and permit those calls.

## Alpha Limitations

* Real-world provider behavior varies by model.
* Ollama tool calling depends on model capability.
* Browser automation is not implemented.
* Workflows currently support a deliberately small schema.
* Undo is best-effort.
* SOVYN is not a sandbox for arbitrary shell execution.

## Debug Timing

Use `--debug` when you need per-turn latency details:

```bash
sovyn --debug "read README.md and summarize it"
py -m sovyn --debug
```

Debug mode reports model-turn timing, tool execution timing, and total task time. Normal mode keeps those details hidden.

## Roadmap

### 0.1 alpha

Terminal agent, permissions, sessions, memory, workflows, and provider abstraction.

### 0.2

Broader real-provider validation, workflow parameters and polish, provider streaming improvements, and community workflows.

### Later

Discord integration, optional browser tools, and workflow sharing.

## Social Preview

Recommended GitHub social preview direction:

```text
SOVYN
Open-source terminal agent

Do it once.
SOVYN learns the workflow.
```

Use a minimal dark, terminal-oriented design. Do not use a fake Discord invite.

## Project Links

* [Repository](https://github.com/gaedsstudio/sovyn)
* [Issues](https://github.com/gaedsstudio/sovyn/issues)
* [Releases](https://github.com/gaedsstudio/sovyn/releases)
* [Contributing](https://github.com/gaedsstudio/sovyn/blob/main/.github/CONTRIBUTING.md)
* [Security](https://github.com/gaedsstudio/sovyn/blob/main/SECURITY.md)
