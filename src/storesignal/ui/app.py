"""Module N - Streamlit UI wired to real pipeline outputs."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from storesignal.config import ROOT

PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

st.set_page_config(page_title="StoreSignal AI", layout="wide")

st.title("StoreSignal AI")
st.caption("Multilingual retail operations early-warning and incident-resolution intelligence")

tab_cc, tab_radar, tab_explorer, tab_brief, tab_trust = st.tabs([
    "Command Center", "Early-Warning Radar", "Incident Explorer",
    "Regional Action Brief", "Model & Trust",
])


@st.cache_data(show_spinner=False)
def load(path, fmt="parquet"):
    p = PROC / path
    if not p.exists():
        return None
    if fmt == "parquet":
        return pd.read_parquet(p)
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


with tab_cc:
    st.subheader("Command Center")
    alerts = load("alerts.parquet")
    escalations = load("escalations.parquet")
    classified = load("classified.parquet")
    if alerts is None or classified is None:
        st.error("Pipeline outputs missing. Run the full pipeline first.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Records processed", f"{len(classified):,}")
        c2.metric("Alerts", f"{len(alerts):,}")
        c3.metric("Policy escalations", f"{len(escalations) if escalations is not None else 0:,}")
        c4.metric("Regions", alerts["region"].nunique() if not alerts.empty else 0)

        st.markdown("### Priority queue (policy first, then rising trend)")
        def rank(row):
            r = row["reason"]
            return (not ("policy_mandatory" in r), not ("rising_trend" in r), -row["total_report_count"])
        ranked = alerts.copy()
        ranked["_rank"] = ranked.apply(rank, axis=1)
        ranked = ranked.sort_values("_rank").head(20)
        st.dataframe(ranked[["alert_id", "store_id", "region", "issue_category", "severity",
                             "suggested_owner", "unique_report_count", "sla_hours"]],
                     use_container_width=True)


with tab_radar:
    st.subheader("Early-Warning Radar")
    det = load("detections.parquet")
    if det is None:
        st.error("Detections missing.")
    else:
        store = st.selectbox("Store", sorted(det["store_id"].unique()))
        cat = st.selectbox("Issue category", sorted(det["issue_category"].unique()))
        sub = det[(det["store_id"] == store) & (det["issue_category"] == cat)].sort_values("date")
        if sub.empty:
            st.info("No data for this store/category.")
        else:
            st.line_chart(sub.set_index("date")[["count", "smoothed_count"]])
            flagged = sub[sub["flagged"]]
            st.markdown(f"**{len(flagged)} flagged days**")
            if not flagged.empty:
                st.dataframe(flagged[["date", "count", "smoothed_count", "baseline_median", "z", "rate_ratio"]],
                             use_container_width=True)


with tab_explorer:
    st.subheader("Incident Explorer")
    incidents = load("incidents.parquet")
    if incidents is None:
        st.error("Incidents missing.")
    else:
        col1, col2 = st.columns(2)
        region = col1.selectbox("Region", ["All"] + sorted(incidents["region"].unique()))
        cat = col2.selectbox("Category", ["All"] + sorted(incidents["issue_category"].unique()))
        view = incidents.copy()
        if region != "All":
            view = view[view["region"] == region]
        if cat != "All":
            view = view[view["issue_category"] == cat]
        st.markdown(f"**{len(view)} incidents**")
        for _, r in view.head(10).iterrows():
            with st.expander(f"{r['incident_id']} - {r['store_id']} - {r['issue_category']} ({r['severity']})"):
                st.write(f"First seen: {r['first_seen']}")
                st.write(f"Channels: {', '.join(r['channels'])}")
                st.write(f"Unique reports: {r['unique_record_count']} / total {r['total_records']}")
                st.write("**Evidence:**")
                for s in r["evidence_snippets"][:3]:
                    st.write(f"- {s[:300]}")


with tab_brief:
    st.subheader("Regional Action Brief")
    region = st.selectbox("Choose region", ["East", "North", "South", "West"])
    path = REPORTS / f"brief_{region}.md"
    if path.exists():
        st.markdown(path.read_text(encoding="utf-8"))
    else:
        st.warning("Run the pipeline to generate briefs.")


with tab_trust:
    st.subheader("Model & Trust")
    eval_path = REPORTS / "evaluation.json"
    if not eval_path.exists():
        st.warning("Evaluation report not yet generated.")
    else:
        report = json.loads(eval_path.read_text(encoding="utf-8"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Macro-F1 (category)", f"{report['macro_f1_category']['macro_f1']:.3f}",
                  help=f"n={report['macro_f1_category']['n']}")
        c2.metric("Escalation precision", f"{report['escalation_precision']['precision']:.3f}",
                  help=f"n={report['escalation_precision']['n']}")
        c3.metric("False alerts / store-week", f"{report['false_alerts_per_store_week']:.3f}")
        st.markdown("### Seeded incident detection")
        st.dataframe(pd.DataFrame(report["detection_lead_time"]), use_container_width=True)
        st.markdown("### Coverage")
        st.write("By channel:", report["coverage"]["by_channel"])
        st.write("By language:", report["coverage"]["by_language"])
        st.markdown("---")
        st.caption("All values above are measured from the pipeline. No simulated placeholders.")


# Additional tabs (appended at bottom so they render below existing tabs)
st.divider()
st.subheader("Feedback & Resolution")

with st.expander("Submit reviewer feedback", expanded=False):
    with st.form("feedback_form"):
        a_id = st.text_input("Alert ID", value="ALERT00001")
        label = st.selectbox("Label", ["correct", "incorrect", "duplicate", "already_resolved", "misrouted"])
        reviewer = st.text_input("Reviewer", value="reviewer-1")
        note = st.text_input("Note", value="")
        submitted = st.form_submit_button("Submit")
        if submitted:
            from storesignal.feedback.loop import submit as fb_submit
            try:
                fb_submit(a_id, label, reviewer, note)
                st.success(f"Recorded feedback for {a_id}")
            except Exception as e:
                st.error(str(e))

with st.expander("Feedback summary", expanded=True):
    from storesignal.feedback.loop import summary as fb_summary
    s = fb_summary()
    st.write(f"Total reviews: {s['total']}")
    if s["by_label"]:
        st.json(s["by_label"])

with st.expander("Incident resolution tracker", expanded=False):
    from storesignal.tracking.tracker import dashboard as tk_dash
    d = tk_dash()
    st.write(f"Stages order: {' -> '.join(d.get('stages_order', []))}")
    if d["incidents"]:
        import pandas as pd
        rows = [{"incident_id": k, "owner": v["owner"], "stages": ", ".join(v["stages"])}
                for k, v in d["incidents"].items()]
        st.dataframe(pd.DataFrame(rows), width="stretch")
    else:
        st.info("No transitions recorded yet.")

st.divider()
st.subheader("Incident Replay")
try:
    import json as _json
    with (PROC / "replay.json").open(encoding="utf-8") as fh:
        replay_data = _json.load(fh)
    inc_choice = st.selectbox("Seeded incident", list(replay_data.keys()))
    data = replay_data[inc_choice]
    st.write(f"Store: {data['store_id']}, Category: {data['category']}")
    st.write(f"Records: {data['n_records']}, First detection: {data['first_detection']}, Lead time: {data['lead_time_days']} days")
    import pandas as pd
    df = pd.DataFrame(data["steps"])
    st.dataframe(df, width="stretch")
except Exception as e:
    st.error(f"Replay data unavailable: {e}")
