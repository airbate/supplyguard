"""Append-only, hash-chained, signed audit log.

Replaces the earlier ``logs_hash="sha256:demo"`` placeholder with a real
tamper-evident chain: every entry hashes the previous entry's hash, and each
hash is HMAC-signed. ``verify()`` walks the chain to detect any tampering.

v1 keeps the log in memory; the append-only shape is identical whether the
backing store is memory, SQLite, or PolarDB — only persistence differs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any


def _canonical(entry: dict[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, default=str)


class AuditLog:
    """A tamper-evident, append-only audit log."""

    def __init__(self, signing_key: bytes | None = None) -> None:
        # Production should inject a real key via SUPPLYGUARD_SIGNING_KEY.
        self._signing_key = signing_key or os.environ.get(
            "SUPPLYGUARD_SIGNING_KEY", "supplyguard-demo-key"
        ).encode("utf-8")
        self._entries: list[dict[str, Any]] = []

    def append(
        self,
        session_id: str,
        event: str,
        verdict: str = "",
        evidence_hash: str = "",
        agent_actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Append an entry and return it (including its hash + signature)."""
        prev_hash = self._entries[-1]["hash"] if self._entries else ""
        body = {
            "session_id": session_id,
            "event": event,
            "verdict": verdict,
            "evidence_hash": evidence_hash,
            "agent_actions": agent_actions or [],
            "prev_hash": prev_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry_hash = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        signature = hmac.new(self._signing_key, entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()

        record = {**body, "hash": entry_hash, "signature": signature}
        self._entries.append(record)
        return record

    def verify(self) -> bool:
        """Return True only if the whole chain is intact and signed."""
        for i, entry in enumerate(self._entries):
            expected_prev = self._entries[i - 1]["hash"] if i > 0 else ""
            if entry.get("prev_hash") != expected_prev:
                return False
            body = {k: v for k, v in entry.items() if k not in ("hash", "signature")}
            if entry.get("hash") != hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest():
                return False
            expected_sig = hmac.new(
                self._signing_key, entry["hash"].encode("utf-8"), hashlib.sha256
            ).hexdigest()
            if entry.get("signature") != expected_sig:
                return False
        return True

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    @property
    def head_hash(self) -> str:
        return self._entries[-1]["hash"] if self._entries else ""
