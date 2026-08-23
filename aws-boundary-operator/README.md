# Boundary Operator

**Boundary Operator** is a Strands Agents professional agent that quietly handles routine developer-operations investigation and only interrupts a human when an actual state-changing decision is required.

This is an isolated competition implementation for the AWS **Agents for Humans** hackathon. It is intentionally separate from production operator code.

## Why this exists

Developers lose time to an awkward class of work: inspect a workspace, interpret policy, run diagnostics, decide whether anything needs changing, make the smallest fix, and prove the fix worked. Most of that can happen in the background. The human should enter only at the irreversible or state-changing boundary.

Boundary Operator implements that loop:

1. **Observe** — scan/read only inside an explicitly authorized workspace root.
2. **Diagnose** — run only named, pre-approved verification commands; no arbitrary shell.
3. **Decide** — Strands reasons over the evidence.
4. **Interrupt at the boundary** — `HumanInTheLoop` allows read-only tools to run freely but requires the user to type `confirm` before `apply_text_patch` can mutate a file.
5. **Verify** — the agent re-reads/re-checks after the mutation.
6. **Prove** — each mutation is written to a hash-chained evidence ledger, and the agent verifies the chain before declaring success.

## Strands usage

The project uses Strands as the actual agent runtime, not as a wrapper:

- `Agent` owns the reasoning/tool loop.
- custom `@tool` functions expose bounded observation, verification, and mutation capabilities.
- `HumanInTheLoop` implements the human decision boundary.
- safe read-only tools are explicitly allowlisted; mutation is fail-closed behind approval.

## Quick start

Requirements: Python 3.10+ and AWS credentials with Bedrock model access (or configure another Strands model provider).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

boundary-operator --root demo_workspace \
  "Inspect this production-service workspace, enforce the documented operational policy if necessary, and verify the result."
```

Expected behavior:

- The agent reads the workspace and policy without interrupting you.
- It should identify `default_timeout_seconds=600` as violating the documented 120-second maximum.
- Before changing `service.conf`, Strands pauses and asks for approval.
- The mutation only proceeds if you type `confirm`.
- The agent then verifies the changed file and the evidence ledger.

Reset the demo with:

```bash
printf 'service=checkout-worker\ndefault_timeout_seconds=600\nmode=production\n' > demo_workspace/service.conf
rm -rf demo_workspace/.boundary_operator
```

## Safety properties in the first slice

- Workspace path traversal is rejected.
- Arbitrary shell commands are not exposed to the model.
- Only named read-only checks can execute without approval.
- File mutation requires exact, unique text replacement and human confirmation.
- Mutation evidence is hash chained and tamper detectable.
- Production repositories are not imported or modified.

## Tests

The core policy and ledger tests do not require model credentials:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Pre-existing work disclosure

The **architecture and safety philosophy** are informed by prior private/public operator-system work by the same author, including supervised execution, allowlisted actions, verification, and tamper-evident logging. This hackathon implementation was written separately during the competition period; no production source files are copied into this project.

## Next evidence gate

This branch earns further build effort only if the first slice demonstrates the complete loop end-to-end under Strands: autonomous read-only investigation -> human-gated mutation -> independent verification -> valid evidence chain. Deployment/UI/AgentCore work waits until that loop is proven.
