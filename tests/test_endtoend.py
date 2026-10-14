"""End-to-end test: pipeline outputs exist and are internally consistent."""
from pathlib import Path

from storesignal.config import ROOT


PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def test_pipeline_outputs_exist():
    for name in ["unified.parquet", "classified.parquet", "escalations.parquet",
                 "detections.parquet", "incidents.parquet", "alerts.parquet",
                 "replay.json"]:
        assert (PROC / name).exists(), f"missing {name}"


def test_evaluation_report_exists():
    assert (REPORTS / "evaluation.json").exists()
    assert (REPORTS / "evaluation.md").exists()


def test_seeded_incidents_all_detected():
    import json
    with (REPORTS / "evaluation.json").open(encoding="utf-8") as fh:
        rep = json.load(fh)
    assert all(r["detected"] for r in rep["detection_lead_time"]), \
        f"missed seeded incidents: {rep['detection_lead_time']}"


def test_escalation_precision_reasonable():
    import json
    with (REPORTS / "evaluation.json").open(encoding="utf-8") as fh:
        rep = json.load(fh)
    assert rep["escalation_precision"]["precision"] >= 0.8


def test_feedback_loop():
    from storesignal.feedback.loop import submit, summary
    submit("ALERT00001", "correct", "reviewer-1", "verified")
    s = summary()
    assert s["total"] >= 1


def test_tracker_transitions():
    from storesignal.tracking.tracker import transition, dashboard
    transition("INC00001", "detected")
    transition("INC00001", "reviewed", owner="Store Ops")
    d = dashboard()
    assert "INC00001" in d["incidents"]
