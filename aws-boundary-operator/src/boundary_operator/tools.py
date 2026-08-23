from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from strands import tool

from .ledger import EvidenceLedger
from .policy import PolicyViolation, WorkspacePolicy, check_command


def _root() -> Path:
    return Path(os.environ.get("BOUNDARY_OPERATOR_ROOT", os.getcwd())).resolve()


def _policy() -> WorkspacePolicy:
    return WorkspacePolicy(_root())


def _ledger() -> EvidenceLedger:
    return EvidenceLedger(_root() / ".boundary_operator" / "evidence.jsonl")


def _preflight_text_patch(path: str, old: str, new: str) -> tuple[Path, str]:
    target = _policy().resolve(path)
    if not target.is_file():
        raise PolicyViolation(f"target is not a file: {path}")
    if not old:
        raise PolicyViolation("old text must be non-empty")
    if old == new:
        raise PolicyViolation("replacement would not change state")
    before = target.read_text(encoding="utf-8")
    occurrences = before.count(old)
    if occurrences == 0:
        raise PolicyViolation("old text was not found; refusing ambiguous patch")
    if occurrences != 1:
        raise PolicyViolation(
            f"old text occurs {occurrences} times; refusing ambiguous patch"
        )
    return target, before


@tool
def scan_workspace() -> str:
    """List a bounded summary of files in the authorized workspace. Read-only."""
    root = _root()
    files: list[str] = []
    for path in root.rglob("*"):
        if ".git" in path.parts or ".boundary_operator" in path.parts:
            continue
        if path.is_file():
            files.append(str(path.relative_to(root)))
        if len(files) >= 100:
            break
    return json.dumps({"root": str(root), "files": sorted(files)}, indent=2)


@tool
def read_text_file(path: str) -> str:
    """Read a UTF-8 text file inside the authorized workspace. Read-only."""
    target = _policy().resolve(path)
    if not target.is_file():
        raise FileNotFoundError(path)
    data = target.read_text(encoding="utf-8")
    return data[:20000]


@tool
def run_safe_check(check: str) -> str:
    """Run one pre-approved read-only verification command in the workspace."""
    command = check_command(check)
    result = subprocess.run(
        command,
        cwd=_root(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return json.dumps(
        {
            "check": check,
            "returncode": result.returncode,
            "stdout": result.stdout[-5000:],
            "stderr": result.stderr[-5000:],
        },
        indent=2,
    )


@tool
def validate_text_patch(path: str, old: str, new: str) -> str:
    """Preflight an exact text replacement without changing state. Call this with the exact same path, old, and new values before requesting approval for apply_text_patch."""
    try:
        _preflight_text_patch(path, old, new)
    except PolicyViolation as exc:
        return json.dumps({"valid": False, "path": path, "reason": str(exc)})
    return json.dumps(
        {
            "valid": True,
            "path": path,
            "reason": "exact replacement exists once and would change state",
        }
    )


@tool
def apply_text_patch(path: str, old: str, new: str) -> str:
    """Replace one exact text fragment in an authorized workspace file. The exact patch must first pass validate_text_patch; this mutates state and requires human approval."""
    target, before = _preflight_text_patch(path, old, new)
    after = before.replace(old, new, 1)
    target.write_text(after, encoding="utf-8")
    digest = _ledger().append(
        "apply_text_patch",
        {"path": path, "old": old, "new": new},
    )
    return json.dumps({"status": "applied", "path": path, "evidence_hash": digest})


@tool
def verify_evidence_ledger() -> str:
    """Verify the hash chain for all mutation evidence. Read-only."""
    return json.dumps({"valid": _ledger().verify()})
