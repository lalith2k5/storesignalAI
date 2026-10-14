"""Module I - Incident replay simulator. No hidden labels, no hardcoding."""

from __future__ import annotations

import json

import pandas as pd
import yaml

from storesignal.config import ROOT


PROC = ROOT / "data" / "processed"
EVAL = ROOT / "data" / "eval"
ANCHOR = pd.Timestamp("2026-10-14", tz="UTC")


def run() -> None:
    with (EVAL / "seeded_incidents.yaml").open(encoding="utf-8") as fh:
        seeded = yaml.safe_load(fh)["incidents"]

    df = pd.read_parquet(PROC / "classified.parquet")
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    detections = pd.read_parquet(PROC / "detections.parquet")
    detections["date"] = pd.to_datetime(detections["date"], utc=True)

    out = {}
    for inc in seeded:
        sub = df[(df["store_id"] == inc["store_id"]) & (df["issue_category"] == inc["category"])].sort_values("ts")
        steps = []
        first_detection = None
        for _, r in sub.iterrows():
            day = r["ts"].floor("D")
            det_row = detections[
                (detections["store_id"] == inc["store_id"]) &
                (detections["issue_category"] == inc["category"]) &
                (detections["date"] == day)
            ]
            flagged = bool(det_row["flagged"].any()) if not det_row.empty else False
            if flagged and first_detection is None:
                first_detection = str(day.date())
            steps.append({
                "timestamp": str(r["ts"]),
                "channel": r["channel"],
                "text": r["text_norm"],
                "flagged_by_detector": flagged,
            })
        lead = None
        if first_detection:
            lead = (ANCHOR - pd.Timestamp(first_detection, tz="UTC")).days
        out[inc["id"]] = {
            "store_id": inc["store_id"],
            "category": inc["category"],
            "n_records": len(steps),
            "first_detection": first_detection,
            "lead_time_days": lead,
            "steps": steps,
        }

    with (PROC / "replay.json").open("w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[replay] wrote {PROC / 'replay.json'}")
    for k, v in out.items():
        print(f"[replay] {k}: {v['n_records']} records, first detection={v['first_detection']}, lead={v['lead_time_days']}")


if __name__ == "__main__":
    run()
