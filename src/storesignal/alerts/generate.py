"""Module F + G - Evidence-backed alerts with owner routing."""

from __future__ import annotations

import json

import pandas as pd

from storesignal.config import ROOT, load_routing, load_risk_policy


PROC = ROOT / "data" / "processed"


def run() -> None:
    routing = load_routing()
    policy = load_risk_policy()
    mandatory = {r.category: r for r in policy.rules}

    incidents = pd.read_parquet(PROC / "incidents.parquet")
    detections = pd.read_parquet(PROC / "detections.parquet")
    escalations = pd.read_parquet(PROC / "escalations.parquet")

    # Flag rising trend incidents
    flagged_det = detections[detections["flagged"]][["store_id", "issue_category"]].drop_duplicates()
    flagged_set = set(zip(flagged_det["store_id"], flagged_det["issue_category"]))

    # Flag policy escalation stores/categories
    policy_set = set(zip(escalations["store_id"], escalations["category"])) if not escalations.empty else set()

    alerts = []
    alert_counter = 0
    for _, inc in incidents.iterrows():
        reasons = []
        if (inc["store_id"], inc["issue_category"]) in flagged_set:
            reasons.append("rising_trend")
        if len(inc["channels"]) > 1:
            reasons.append("cross_channel")
        is_policy = (inc["store_id"], inc["issue_category"]) in policy_set or inc["issue_category"] in mandatory
        if is_policy:
            reasons.append("policy_mandatory")

        if not reasons:
            continue

        alert_counter += 1
        aid = f"ALERT{alert_counter:05d}"

        cat = inc["issue_category"]
        if cat in mandatory:
            owner = mandatory[cat].route_to
            sla = mandatory[cat].sla_hours
            action = f"Immediate {owner} review per policy v{policy.policy_version}"
            severity = "critical"
        elif cat in routing.routes:
            owner = routing.routes[cat].owner
            sla = routing.routes[cat].sla_hours
            action = routing.routes[cat].first_action
            severity = inc["severity"]
        else:
            owner = "Store Ops"
            sla = routing.default_sla_hours
            action = "Review incident and assign owner"
            severity = inc["severity"]

        alerts.append({
            "alert_id": aid,
            "incident_id": inc["incident_id"],
            "store_id": inc["store_id"],
            "region": inc["region"],
            "issue_category": cat,
            "severity": severity,
            "reason": reasons,
            "evidence_snippets": inc["evidence_snippets"],
            "channels": inc["channels"],
            "time_window_start": str(inc["first_seen"]),
            "time_window_end": str(inc["last_seen"]),
            "unique_report_count": int(inc["unique_record_count"]),
            "total_report_count": int(inc["total_records"]),
            "dedup_notes": f"{int(inc['total_records']) - int(inc['unique_record_count'])} duplicate reports collapsed",
            "confidence": float(inc["max_confidence"]),
            "suggested_owner": owner,
            "suggested_action": action,
            "escalation_rule": f"policy_v{policy.policy_version}" if is_policy else None,
            "sla_hours": sla,
        })

    out = pd.DataFrame(alerts)
    out.to_parquet(PROC / "alerts.parquet", index=False)
    print(f"[alerts] {len(out)} alerts generated")
    if not out.empty:
        print(f"[alerts] by reason: {out['reason'].map(lambda r: ','.join(r)).value_counts().head().to_dict()}")
        print(f"[alerts] policy alerts: {(out['escalation_rule'].notna()).sum()}")


if __name__ == "__main__":
    run()
