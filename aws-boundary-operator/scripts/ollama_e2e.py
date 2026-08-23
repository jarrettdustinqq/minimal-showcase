from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from strands.models.ollama import OllamaModel

from boundary_operator.agent import make_agent
from boundary_operator.ledger import EvidenceLedger


def main() -> None:
    source = Path(__file__).resolve().parents[1] / "demo_workspace"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copy2(source / "POLICY.md", root / "POLICY.md")
        shutil.copy2(source / "service.conf", root / "service.conf")

        approvals: list[str] = []

        def approve(prompt: str, **_: Any) -> str:
            approvals.append(prompt)
            return "confirm"

        os.environ["BOUNDARY_OPERATOR_ROOT"] = str(root.resolve())
        model = OllamaModel(
            host="http://127.0.0.1:11434",
            model_id=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
            temperature=0,
        )
        agent = make_agent(model=model, ask=approve)
        agent(
            "Inspect the authorized workspace. Read POLICY.md and service.conf. "
            "If service.conf violates the policy, determine the minimum exact text replacement, "
            "preflight that exact replacement with validate_text_patch, and only if validation "
            "succeeds request apply_text_patch. Then reread service.conf and verify the evidence "
            "ledger before declaring success."
        )

        config = (root / "service.conf").read_text(encoding="utf-8")
        if "default_timeout_seconds=120" not in config:
            raise SystemExit("real model did not perform the required bounded correction")
        if len(approvals) != 1:
            raise SystemExit(f"expected exactly one human approval, got {len(approvals)}")

        ledger = EvidenceLedger(root / ".boundary_operator" / "evidence.jsonl")
        if not ledger.path.exists() or not ledger.verify():
            raise SystemExit("evidence ledger missing or invalid after real-model run")
        if len(ledger.path.read_text(encoding="utf-8").splitlines()) != 1:
            raise SystemExit("expected exactly one mutation evidence record")

        print("Ollama end-to-end evidence gate passed")


if __name__ == "__main__":
    main()
