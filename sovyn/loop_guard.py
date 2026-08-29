from dataclasses import dataclass, field
from hashlib import sha256


@dataclass(slots=True)  # noqa: MUTABLE_OK
class LoopGuard:
    limit: int
    fingerprints: list[str] = field(default_factory=list)

    def observe(self, tool_name: str, arguments: str) -> str | None:
        fingerprint = sha256(f"{tool_name}:{arguments}".encode("utf-8")).hexdigest()
        self.fingerprints.append(fingerprint)
        if len(self.fingerprints) >= self.limit and len(set(self.fingerprints[-self.limit :])) == 1:
            return "Repeated action detected"
        if len(self.fingerprints) >= 4 and self.fingerprints[-4] == self.fingerprints[-2] and self.fingerprints[-3] == self.fingerprints[-1]:
            return "Alternating action loop detected"
        return None
