# Launch Post Drafts

## Hacker News

Title:

```text
Show HN: SOVYN - A local-first terminal agent that turns work into reusable workflows
```

Body:

```text
I built SOVYN, an open-source terminal agent focused on explicit permissions and reusable workflows.

It runs in your workspace, supports local Ollama or BYOK providers, and asks before file writes, sensitive shell commands, or cloud-context fallback. The part I care about most is workflow capture: after a successful task, SOVYN can save the tool sequence as an editable workflow and replay it later.

This is a public alpha, not a finished product. The current scope is intentionally small: terminal agent loop, sessions, memory, workflows, provider abstraction, diagnostics, and a deterministic benchmark. Real provider behavior still needs more community validation.

Repo: https://github.com/gaedsstudio/sovyn
```

## Reddit

```text
I am releasing the first public alpha of SOVYN, an open-source terminal agent for local-first workflows.

The design is deliberately conservative: SOVYN can use Ollama or BYOK providers, asks before file writes / sensitive shell commands / network or cloud-context actions, records sessions locally, and can turn successful tool sequences into editable workflows.

It is alpha software. Ollama support is implemented but real-host tool-calling was not manually verified on my release machine because Ollama was not installed. I am especially interested in provider compatibility reports and workflow UX feedback.

https://github.com/gaedsstudio/sovyn
```

## Future Discord Announcement

```text
SOVYN v0.1.0a1 is out as a public alpha.

SOVYN is an open-source terminal agent that runs local tools with explicit permissions and turns successful work into reusable workflows. The first release includes the terminal agent loop, sessions, memory, workflow replay, provider normalization, diagnostics, and a small deterministic benchmark.

Please treat it as alpha software: use Git, review prompts carefully, and share provider compatibility reports.

https://github.com/gaedsstudio/sovyn
```
