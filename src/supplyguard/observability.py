"""Lightweight structured logging + span tracing.

Implements the design doc's §7.3 Trace + Log selection with the stdlib only
(no OpenTelemetry dependency in v1). ``log_event`` emits one-line JSON records
carrying the agreed fields (session_id, agent_id, skill_name, event, ...), and
``span`` records start/end/duration around each agent invocation. Swapping the
emitter for an OTLP exporter later is a one-line change.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("supplyguard")


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured JSON log record."""
    payload: dict[str, Any] = {"event": event, **fields}
    logger.log(level, json.dumps(payload, default=str))


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    """Record a span around a block, returning a dict that gains duration_ms."""
    start = time.perf_counter()
    log_event("span.start", name=name, **attrs)
    result: dict[str, Any] = {}
    try:
        yield result
    finally:
        result["duration_ms"] = round((time.perf_counter() - start) * 1000, 3)
        log_event("span.end", name=name, duration_ms=result["duration_ms"], **attrs)
