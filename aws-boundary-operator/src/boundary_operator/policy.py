from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PolicyViolation(ValueError):
    """Raised when an operation exceeds the configured execution boundary."""


@dataclass(frozen=True)
class WorkspacePolicy:
    root: Path

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        root = self.root.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise PolicyViolation(f"path escapes workspace: {relative_path}") from exc
        return candidate


SAFE_CHECKS: dict[str, tuple[str, ...]] = {
    "python_compile": ("python3", "-m", "compileall", "-q", "."),
    "git_status": ("git", "status", "--short"),
    "git_diff_check": ("git", "diff", "--check"),
}


def check_command(name: str) -> tuple[str, ...]:
    try:
        return SAFE_CHECKS[name]
    except KeyError as exc:
        raise PolicyViolation(f"unsupported check: {name}") from exc
