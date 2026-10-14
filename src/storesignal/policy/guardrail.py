"""Module E - Safety-first guardrail.

Reads predictions, applies mandatory-risk rules from risk_policy.yaml,
produces escalations independent of volume, trend, or confidence.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from storesignal.config import ROOT, load_risk_policy


PROC = ROOT / "data" / "processed"


def run() -> None:
    policy = load_risk_policy()
    mandatory = {r.category: r for r in policy.rules}

    df = pd.read_parquet(PROC / "classified.parquet")
    rows = []
    for _, r in df.iterrows():
        cat = r["issue_category"]
        if cat in mandatory:
            rule = mandatory[cat]
            rows.append({
                "record_id": r["record_id"],
                "store_id": r["store_id"],
                "region": r["region"],
                "category": cat,
                "severity": r["severity"],
                "route_to": rule.route_to,
                "sla_hours": rule.sla_hours,
                "reason": "policy_mandatory",
                "independent_of_volume": True,
                "policy_version": policy.policy_version,
            })
    esc = pd.DataFrame(rows)
    if esc.empty:
        esc = pd.DataFrame(columns=[
            "record_id", "store_id", "region", "category", "severity",
            "route_to", "sla_hours", "reason", "independent_of_volume", "policy_version",
        ])
    esc.to_parquet(PROC / "escalations.parquet", index=False)
    print(f"[policy] {len(esc)} escalations (policy_mandatory)")
    if not esc.empty:
        print(f"[policy] by category: {esc['category'].value_counts().to_dict()}")


if __name__ == "__main__":
    run()
