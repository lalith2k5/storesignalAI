"""Module L - Incident-to-resolution tracker."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from storesignal.config import ROOT

PROC = ROOT / "data" / "processed"
TRACK_FILE = PROC / "tracker.jsonl"
STAGES = ["detected", "reviewed", "assigned", "action_taken", "resolved"]


def transition(incident_id: str, stage: str, owner: str = "", note: str = "") -> dict:
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    entry = {
        "incident_id": incident_id,
        "stage": stage,
        "owner": owner,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    PROC.mkdir(parents=True, exist_ok=True)
    with TRACK_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def dashboard() -> dict:
    if not TRACK_FILE.exists():
        return {"incidents": {}}
    by_incident: dict[str, dict] = {}
    with TRACK_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            e = json.loads(line)
            by_incident.setdefault(e["incident_id"], {"stages": [], "owner": ""})["stages"].append(e["stage"])
            if e["owner"]:
                by_incident[e["incident_id"]]["owner"] = e["owner"]
    return {"incidents": by_incident, "stages_order": STAGES}
