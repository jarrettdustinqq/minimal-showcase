import json
import tempfile
import unittest
from pathlib import Path

from boundary_operator.ledger import EvidenceLedger


class EvidenceLedgerTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            ledger = EvidenceLedger(path)
            ledger.append("first", {"value": 1})
            ledger.append("second", {"value": 2})
            self.assertTrue(ledger.verify())

            lines = path.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            record["details"]["value"] = 999
            lines[0] = json.dumps(record, sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(ledger.verify())


if __name__ == "__main__":
    unittest.main()
