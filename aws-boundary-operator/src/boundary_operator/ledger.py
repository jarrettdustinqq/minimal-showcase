from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class EvidenceLedger:
    path: Path

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return GENESIS
        last = self.path.read_text(encoding="utf-8").strip().splitlines()[-1]
        return json.loads(last)["hash"]

    def append(self, event: str, details: dict[str, Any]) -> str:
        previous = self._last_hash()
        body = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
            "previous_hash": previous,
        }
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        record = {**body, "hash": digest}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return digest

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        previous = GENESIS
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            claimed = record.pop("hash")
            if record["previous_hash"] != previous:
                return False
            if hashlib.sha256(_canonical(record)).hexdigest() != claimed:
                return False
            previous = claimed
        return True
