"""Module K - Human feedback loop (error analysis only, no auto-retrain)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from storesignal.config import ROOT

PROC = ROOT / "data" / "processed"
FEEDBACK_FILE = PROC / "feedback.jsonl"

VALID_LABELS = {"correct", "incorrect", "duplicate", "already_resolved", "misrouted"}


def submit(alert_id: str, label: str, reviewer_id: str, note: str = "") -> dict:
    if label not in VALID_LABELS:
        raise ValueError(f"label must be one of {sorted(VALID_LABELS)}")
    entry = {
        "alert_id": alert_id,
        "label": label,
        "reviewer_id": reviewer_id,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    PROC.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def summary() -> dict:
    if not FEEDBACK_FILE.exists():
        return {"total": 0, "by_label": {}}
    counts: dict[str, int] = {}
    total = 0
    with FEEDBACK_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            e = json.loads(line)
            counts[e["label"]] = counts.get(e["label"], 0) + 1
            total += 1
    return {"total": total, "by_label": counts}
