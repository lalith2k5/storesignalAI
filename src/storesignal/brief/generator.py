"""Module H - Regional weekly brief generator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from storesignal.config import ROOT, load_thresholds


PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def run() -> None:
    cfg = load_thresholds().brief
    alerts = pd.read_parquet(PROC / "alerts.parquet")
    REPORTS.mkdir(parents=True, exist_ok=True)

    for region, g in alerts.groupby("region"):
        g = g.copy()
        # Ranking: policy first, then rising trend, then volume
        def rank(row):
            r = row["reason"]
            policy = "policy_mandatory" in r
            trend = "rising_trend" in r
            return (not policy, not trend, -row["total_report_count"])
        g["_rank"] = g.apply(rank, axis=1)
        g = g.sort_values("_rank").head(cfg.top_n)

        lines = [f"# Weekly Action Brief - {region}", ""]
        lines.append("## 1. Executive summary")
        for _, r in g.head(3).iterrows():
            lines.append(f"- {r['issue_category']} at {r['store_id']} (severity {r['severity']}, reasons: {', '.join(r['reason'])})")
        lines.append("")
        lines.append(f"## 2. Priority incidents (top {cfg.top_n})")
        for _, r in g.iterrows():
            lines.append(f"### {r['issue_category']} - {r['store_id']}")
            lines.append(f"- Severity: {r['severity']}")
            lines.append(f"- Owner: {r['suggested_owner']} (SLA {r['sla_hours']}h)")
            lines.append(f"- Next step: {r['suggested_action']}")
            lines.append(f"- Evidence ({r['unique_report_count']} unique reports, {r['dedup_notes']}):")
            for s in r["evidence_snippets"][:3]:
                lines.append(f"  - \"{s[:200]}\"")
            lines.append("")
        lines.append("## 3. Emerging signals")
        emerging = alerts[alerts["reason"].map(lambda r: "rising_trend" in r)]
        for _, r in emerging.head(5).iterrows():
            lines.append(f"- {r['store_id']} {r['issue_category']}: rising trend, {r['unique_report_count']} unique reports")
        lines.append("")
        lines.append("## 4. Safety and compliance")
        safety = alerts[alerts["reason"].map(lambda r: "policy_mandatory" in r)]
        for _, r in safety.head(5).iterrows():
            lines.append(f"- {r['store_id']} {r['issue_category']} -> {r['suggested_owner']} (SLA {r['sla_hours']}h)")
        lines.append("")
        lines.append("## 5. Actions due")
        lines.append("- See incident tracker (Module L).")
        lines.append("")
        lines.append("## 6. Data caveats")
        lines.append("- Detection seasonality not modeled in MVP.")
        lines.append("- Where exposure denominators missing, size-band proxy used.")

        out = REPORTS / f"brief_{region.replace(' ', '_')}.md"
        with out.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        print(f"[brief] wrote {out} ({len(g)} incidents)")


if __name__ == "__main__":
    run()
