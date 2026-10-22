from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from strands import Agent
from strands.interventions import Deny, InterventionHandler, Proceed
from strands.vended_interventions.hitl import HumanInTheLoop

from .policy import PolicyViolation
from .tools import (
    _preflight_text_patch,
    apply_text_patch,
    read_text_file,
    run_safe_check,
    scan_workspace,
    validate_text_patch,
    verify_evidence_ledger,
)

SYSTEM_PROMPT = """You are Boundary Operator, a professional background operations agent.
Your job is to investigate routine developer-workspace problems, perform safe read-only diagnostics without interruption, and surface a human only at the decision boundary before a state-changing action.

Operating rules:
1. Inspect before proposing changes.
2. Prefer read-only tools and pre-approved checks.
3. Never invent shell commands; only use the provided tools.
4. Before every apply_text_patch call, call validate_text_patch with the exact same path, old, and new values. Only request the mutation if validation returns valid=true.
5. A mutation is not complete until you independently reread or recheck the affected state and verify the evidence ledger.
6. If a mutation is unnecessary or its exact patch fails preflight, do not ask a human to approve it.
7. Explain the concrete reason for any requested mutation in one sentence.
"""


class PatchPreflightGuard(InterventionHandler):
    """Reject malformed mutations before the human approval handler can run."""

    name = "patch-preflight-guard"

    def before_tool_call(self, event):
        if event.tool_use.get("name") != "apply_text_patch":
            return Proceed()

        tool_input = event.tool_use.get("input", {})
        try:
            path = tool_input["path"]
            old = tool_input["old"]
            new = tool_input["new"]
            if not all(isinstance(value, str) for value in (path, old, new)):
                raise PolicyViolation("path, old, and new must all be strings")
            _preflight_text_patch(path, old, new)
        except (KeyError, PolicyViolation) as exc:
            return Deny(
                reason=(
                    "Mutation preflight failed before human approval: "
                    f"{exc}. Re-read the target and retry with one exact, unique replacement."
                )
            )
        return Proceed()


def make_agent(*, model: Any | None = None, ask: Any = "stdio") -> Agent:
    """Construct Boundary Operator, allowing deterministic model/approval injection in tests."""
    kwargs: dict[str, Any] = {}
    if model is not None:
        kwargs["model"] = model
    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            scan_workspace,
            read_text_file,
            run_safe_check,
            validate_text_patch,
            apply_text_patch,
            verify_evidence_ledger,
        ],
        interventions=[
            PatchPreflightGuard(),
            HumanInTheLoop(
                ask=ask,
                allowed_tools=[
                    "scan_workspace",
                    "read_text_file",
                    "run_safe_check",
                    "validate_text_patch",
                    "verify_evidence_ledger",
                ],
                evaluate=lambda response: isinstance(response, str)
                and response.strip().lower() == "confirm",
            ),
        ],
        **kwargs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Boundary Operator")
    parser.add_argument("task", nargs="*", help="Task for the agent")
    parser.add_argument(
        "--root",
        default=os.getcwd(),
        help="Authorized workspace root (default: current directory)",
    )
    args = parser.parse_args()
    os.environ["BOUNDARY_OPERATOR_ROOT"] = str(Path(args.root).resolve())
    task = " ".join(args.task).strip() or (
        "Inspect this workspace for an obvious operational problem, fix it only if needed, "
        "and verify the result."
    )
    make_agent()(task)


if __name__ == "__main__":
    main()
