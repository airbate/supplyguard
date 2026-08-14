"""Unit tests for the append-only, signed audit log."""

from __future__ import annotations

from supplyguard.audit import AuditLog


def test_empty_log_verifies() -> None:
    assert AuditLog().verify() is True


def test_chain_is_linked_and_signed() -> None:
    log = AuditLog(signing_key=b"test-key")
    log.append("s1", event="verdict", verdict="block")
    log.append("s1", event="sealed")

    assert log.verify() is True
    assert log.entries[1]["prev_hash"] == log.entries[0]["hash"]
    assert log.head_hash == log.entries[-1]["hash"]


def test_tampering_is_detected() -> None:
    log = AuditLog(signing_key=b"test-key")
    log.append("s1", event="verdict", verdict="block")

    # Rewrite the stored verdict after the fact.
    log._entries[0]["verdict"] = "allow"
    assert log.verify() is False


def test_append_is_order_dependent() -> None:
    log = AuditLog(signing_key=b"test-key")
    log.append("s1", event="verdict", verdict="block")

    # Forging a second entry whose prev_hash is empty should not verify.
    forged = dict(log.entries[0])
    forged["prev_hash"] = ""
    log._entries.append(forged)
    assert log.verify() is False
