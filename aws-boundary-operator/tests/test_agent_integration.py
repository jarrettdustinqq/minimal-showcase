import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from strands.models import Model

from boundary_operator.agent import make_agent
from boundary_operator.ledger import EvidenceLedger


class ScriptedToolModel(Model):
    """Deterministic Strands model that drives one complete Boundary Operator loop."""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {"model_id": "scripted-tool-model"}
        self.turn = 0
        self.actions = [
            ("scan_workspace", {}),
            ("read_text_file", {"path": "POLICY.md"}),
            ("read_text_file", {"path": "service.conf"}),
            (
                "apply_text_patch",
                {
                    "path": "service.conf",
                    "old": "default_timeout_seconds=600",
                    "new": "default_timeout_seconds=120",
                },
            ),
            ("read_text_file", {"path": "service.conf"}),
            ("verify_evidence_ledger", {}),
        ]

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return dict(self.config)

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        if False:
            yield {}
        raise NotImplementedError("structured output is not used by this deterministic test model")

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        yield {"messageStart": {"role": "assistant"}}

        if self.turn < len(self.actions):
            name, payload = self.actions[self.turn]
            tool_use_id = f"scripted-{self.turn}"
            yield {
                "contentBlockStart": {
                    "start": {
                        "toolUse": {"name": name, "toolUseId": tool_use_id}
                    }
                }
            }
            yield {
                "contentBlockDelta": {
                    "delta": {"toolUse": {"input": json.dumps(payload)}}
                }
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {
                "contentBlockDelta": {
                    "delta": {"text": "Verified the bounded change and evidence chain."}
                }
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}

        self.turn += 1


class AgentIntegrationTests(unittest.TestCase):
    def test_real_strands_loop_gates_mutation_then_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "POLICY.md").write_text(
                "default_timeout_seconds must not exceed 120\n", encoding="utf-8"
            )
            config = root / "service.conf"
            config.write_text(
                "service=checkout-worker\ndefault_timeout_seconds=600\nmode=production\n",
                encoding="utf-8",
            )
            prompts: list[str] = []

            def approve(prompt: str, **kwargs: Any) -> str:
                prompts.append(prompt)
                return "confirm"

            with patch.dict(
                os.environ, {"BOUNDARY_OPERATOR_ROOT": str(root.resolve())}, clear=False
            ):
                agent = make_agent(model=ScriptedToolModel(), ask=approve)
                agent("Inspect, enforce policy only if necessary, and verify the result.")

            self.assertEqual(len(prompts), 1, "only the mutating tool should require approval")
            self.assertIn("default_timeout_seconds=120", config.read_text(encoding="utf-8"))
            ledger = EvidenceLedger(root / ".boundary_operator" / "evidence.jsonl")
            self.assertTrue(ledger.verify())
            self.assertEqual(len(ledger.path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
