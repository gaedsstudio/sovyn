# Contributing

SOVYN is a terminal-native, local-first open-source agent. Contributions should keep the project small, transparent, recoverable, and testable.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Guidelines

- Keep workflows readable and portable.
- Do not add mandatory cloud services.
- Do not log secrets, tokens, or API keys.
- Keep provider-specific code behind provider interfaces.
- Prefer small composable tools over broad magical tools.
- Add tests for permissions, workflow replay, storage, terminal rendering, and reliability changes.
- Keep safety and permission decisions deterministic.
- Avoid unnecessary network dependencies or telemetry.
- Preserve local-first operation whenever possible.

## Project

SOVYN was created by **Seowon Jang ([@gaedsstudio](https://github.com/gaedsstudio))**.

### Founding Developer

**Seowon Jang** — [@gaedsstudio](https://github.com/gaedsstudio)

Creator and founding developer of SOVYN. Led the initial design and implementation of the project, including the terminal agent runtime, local model integration, reliability system, workflow execution, and early remote-agent experiments.

## Contributors

SOVYN is built as an open-source project.

Contributions through code, documentation, testing, design, bug reports, ideas, and feedback are welcome.

Git history remains the authoritative record of individual code contributions.
