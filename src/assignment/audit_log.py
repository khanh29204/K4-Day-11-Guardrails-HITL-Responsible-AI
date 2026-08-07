"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, float] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """TODO: store input + start timestamp keyed by request_id/user_id."""
        rid = request_id or f"req-{len(self.logs):04d}"
        self._open[rid] = time.time()
        self.logs.append({
            "event": "input",
            "request_id": rid,
            "user_id": user_id,
            "text": text,
            "timestamp": utc_now_iso(),
        })
        # raise NotImplementedError("Implement AuditLogPlugin.record_input")

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ):
        """TODO: store output, layer decision, latency; append to self.logs."""
        rid = request_id or f"req-{len(self.logs):04d}"
        started = self._open.pop(rid, None)    # đóng cặp input-output
        latency = (time.time() - started) if started is not None else None
        self.logs.append({
            "event": "output",
            "request_id": rid,
            "user_id": user_id,
            "text": text,
            "blocked": blocked,
            "layer": layer,
            "latency_ms": round(latency * 1000, 1) if latency is not None else None,
            "timestamp": utc_now_iso(),
        })
        # raise NotImplementedError("Implement AuditLogPlugin.record_output")

    def export_json(self, filepath: str = "outputs/audit_log.json"):
        """Write logs to disk (JSON array)."""
        # TODO: ensure parent dirs exist, dump self.logs with indent=2
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.logs, ensure_ascii=False, indent=2), encoding="utf-8")
        # raise NotImplementedError("Implement AuditLogPlugin.export_json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
