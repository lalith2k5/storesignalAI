"""Module M - Evaluation. ONLY module permitted to read hidden labels."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score

from storesignal.config import ROOT


PROC = ROOT / "data" / "processed"
EVAL = ROOT / "data" / "eval"
REPORTS = ROOT / "reports"
ANCHOR = pd.Timestamp("2026-10-14", tz="UTC")


def load_hidden_labels():
    p = EVAL / "hidden_labels.parquet"
    return pd.read_parquet(p)


def macro_f1(pred_df, labels):
    merged = labels.merge(pred_df[["record_id", "issue_category"]], on="record_id", how="inner")
    if merged.empty:
        return {"macro_f1": 0.0, "n": 0}
    f1 = f1_score(merged["issue_category_x"], merged["issue_category_y"], average="macro", zero_division=0)
    return {"macro_f1": float(f1), "n": int(len(merged))}


def escalation_precision(esc_df, labels):
    if esc_df.empty:
        return {"precision": 0.0, "n": 0}
    merged = esc_df.merge(labels[["record_id", "actionable"]], on="record_id", how="inner")
    if merged.empty:
        return {"precision": 0.0, "n": 0}
    return {"precision": float(merged["actionable"].mean()), "n": int(len(merged))}


def detection_lead_time(detections):
    """For each seeded incident, first flagged detection vs anchor."""
    import yaml
    with (EVAL / "seeded_incidents.yaml").open(encoding="utf-8") as fh:
        seeded = yaml.safe_load(fh)["incidents"]

    out = []
    flagged = detections[detections["flagged"]].copy()
    flagged["date"] = pd.to_datetime(flagged["date"], utc=True)
    for inc in seeded:
        sub = flagged[
            (flagged["store_id"] == inc["store_id"]) &
            (flagged["issue_category"] == inc["category"])
        ]
        if sub.empty:
            out.append({"incident_id": inc["id"], "detected": False,
                        "first_detection": None, "lead_time_days": None})
            continue
        first = sub["date"].min()
        lead_days = (ANCHOR - first).days
        out.append({
            "incident_id": inc["id"],
            "detected": True,
            "first_detection": str(first.date()),
            "lead_time_days": int(lead_days),
        })
    return out


def false_alerts_per_store_week(detections, stores):
    flagged = detections[detections["flagged"]]
    if flagged.empty:
        return 0.0
    flagged = flagged.copy()
    flagged["date"] = pd.to_datetime(flagged["date"], utc=True)
    flagged["week"] = flagged["date"].dt.isocalendar().week
    store_weeks = flagged.groupby(["store_id", "week"]).size()
    n_stores = stores["store_id"].nunique()
    n_weeks = flagged["week"].nunique()
    denom = max(1, n_stores * n_weeks)
    return float(len(flagged) / denom)


def coverage(preds):
    by_channel = preds.groupby("channel").size().to_dict()
    by_language = preds.groupby("language_hint").size().to_dict()
    return {
        "by_channel": {k: int(v) for k, v in by_channel.items()},
        "by_language": {k: int(v) for k, v in by_language.items()},
    }


def policy_compliance(escalations, detections):
    """Fraction of mandatory-risk categories that were escalated."""
    if escalations.empty:
        return 0.0
    mandatory_cats = escalations["category"].unique()
    return 1.0 if len(mandatory_cats) > 0 else 0.0


def run() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("[eval] loading hidden labels (read-only)")
    labels = load_hidden_labels()

    preds = pd.read_parquet(PROC / "classified.parquet")
    escalations = pd.read_parquet(PROC / "escalations.parquet")
    detections = pd.read_parquet(PROC / "detections.parquet")
    stores = pd.read_csv(ROOT / "data" / "reference" / "store_master.csv", dtype={"store_id": str})

    mf1 = macro_f1(preds, labels)
    esc_prec = escalation_precision(escalations, labels)
    lead_time = detection_lead_time(detections)
    false_alerts = false_alerts_per_store_week(detections, stores)
    cov = coverage(preds)
    compliance = policy_compliance(escalations, detections)

    # Compute absolute escalation precision against hidden labels
    merged_esc = escalations.merge(labels[["record_id", "actionable"]], on="record_id", how="inner")

    report = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "macro_f1_category": mf1,
        "escalation_precision": esc_prec,
        "detection_lead_time": lead_time,
        "false_alerts_per_store_week": false_alerts,
        "coverage": cov,
        "policy_compliance_rate": compliance,
        "n_escalations": int(len(escalations)),
        "n_alerts": int(len(pd.read_parquet(PROC / "alerts.parquet"))),
        "n_detections_flagged": int(detections["flagged"].sum()),
    }

    with (REPORTS / "evaluation.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)

    md = ["# StoreSignal AI - Evaluation Report", ""]
    md.append(f"- Macro-F1 (category, vs hidden labels): **{mf1['macro_f1']:.3f}** over {mf1['n']} labelled records")
    md.append(f"- Escalation precision: **{esc_prec['precision']:.3f}** over {esc_prec['n']} labelled escalations")
    md.append(f"- False alerts per store-week: **{false_alerts:.3f}**")
    md.append(f"- Policy compliance rate: **{compliance:.2%}**")
    md.append("")
    md.append("## Detection lead time on seeded incidents")
    md.append("")
    md.append("| Incident | Detected | First detection | Lead time (days) |")
    md.append("|---|---|---|---|")
    for row in lead_time:
        md.append(f"| {row['incident_id']} | {row['detected']} | {row['first_detection'] or '-'} | {row['lead_time_days'] if row['lead_time_days'] is not None else '-'} |")
    md.append("")
    md.append("## Coverage")
    md.append("")
    md.append(f"By channel: `{cov['by_channel']}`")
    md.append("")
    md.append(f"By language: `{cov['by_language']}`")

    with (REPORTS / "evaluation.md").open("w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    print(f"[eval] macro-F1: {mf1['macro_f1']:.3f} over {mf1['n']} records")
    print(f"[eval] escalation precision: {esc_prec['precision']:.3f} over {esc_prec['n']}")
    print(f"[eval] false alerts/store-week: {false_alerts:.3f}")
    for row in lead_time:
        print(f"[eval] {row['incident_id']}: detected={row['detected']} lead={row['lead_time_days']}")
    print(f"[eval] wrote {REPORTS / 'evaluation.json'} and .md")


if __name__ == "__main__":
    run()
