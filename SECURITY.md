# Security

Do not report sensitive vulnerabilities in public issues.

Email: SECURITY_CONTACT

SOVYN is local-first and should never log API keys, secrets, tokens, or unrelated file contents. Destructive actions must require explicit confirmation or be blocked by default.

## Model And Tool Safety

SOVYN does not make arbitrary shell execution safe merely because a model requested it.

Shell execution is risky. SOVYN rejects known destructive patterns before prompting, but users should still inspect commands before approving them.

Cloud provider use can expose task prompts, tool observations, filenames, diffs, or file excerpts needed to answer a request. BYOK credentials are read from environment variables and are not written to SOVYN config files by default.

Workspace trust means SOVYN may inspect and modify files under that workspace after explicit permissions. Path validation prevents `../` traversal, Windows drive escape, UNC/network paths, and symlink parent escape where practical.

Local model safety depends on the selected model. If a model does not expose native tool calling, compatibility mode is less reliable and is labeled as such.
