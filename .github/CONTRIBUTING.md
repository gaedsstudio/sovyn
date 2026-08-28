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
- Do not log secrets or API keys.
- Keep provider-specific code behind provider interfaces.
- Prefer small composable tools over broad magical tools.
- Add tests for permissions, workflow replay, storage, and terminal rendering changes.
