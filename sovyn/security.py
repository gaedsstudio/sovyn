import re


SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s]+)"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
)


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: match.group(0).replace(match.group(2), "[REDACTED]") if len(match.groups()) >= 2 else "[REDACTED]", redacted)
    return redacted


def has_sensitive_content(path: str, value: str) -> bool:
    sensitive_name = path.endswith((".env", ".pem", ".key")) or "credential" in path.lower()
    return sensitive_name or any(pattern.search(value) is not None for pattern in SECRET_PATTERNS)
