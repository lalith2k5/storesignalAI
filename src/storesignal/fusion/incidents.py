"""Module D - Cross-channel incident fusion and deduplication."""

from __future__ import annotations

import hashlib

import pandas as pd

from storesignal.config import ROOT, load_thresholds


PROC = ROOT / "data" / "processed"


def dedup_key(text: str, store: str, day) -> str:
    h = hashlib.md5(f"{store}|{day}|{text}".encode("utf-8")).hexdigest()
    return h


def run() -> None:
    cfg = load_thresholds().fusion
    df = pd.read_parquet(PROC / "classified.parquet")
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df["day"] = df["ts"].dt.floor("D")

    # Dedup: exact hash
    df["dup_group_id"] = [
        dedup_key(t, s, d)
        for t, s, d in zip(df["text_norm"].tolist(), df["store_id"].tolist(), df["day"].tolist())
    ]

    # Near-duplicate: token_set_ratio within store-day
    from rapidfuzz.fuzz import token_set_ratio
    dup_ids = df["dup_group_id"].tolist()
    for (_, _), idx in df.groupby(["store_id", "day"]).groups.items():
        idx = list(idx)
        if len(idx) < 2:
            continue
        for i in range(len(idx)):
            for j in range(i + 1, len(idx)):
                a = df.at[idx[i], "text_norm"]
                b = df.at[idx[j], "text_norm"]
                if not a or not b:
                    continue
                score = token_set_ratio(a, b) / 100.0
                if score >= cfg.similarity_threshold:
                    dup_ids[idx[j]] = dup_ids[idx[i]]
    df["dup_group_id"] = dup_ids

    # Fusion: group by store + category, walk forward with time window
    incidents = []
    inc_counter = 0
    window = pd.Timedelta(hours=cfg.time_window_hours)

    for (store, cat), g in df.groupby(["store_id", "issue_category"]):
        g = g.sort_values("ts").reset_index(drop=True)
        visited = [False] * len(g)
        for i in range(len(g)):
            if visited[i]:
                continue
            anchor_ts = g.at[i, "ts"]
            group_idx = [i]
            visited[i] = True
            for j in range(i + 1, len(g)):
                if visited[j]:
                    continue
                if g.at[j, "ts"] - anchor_ts <= window:
                    # Require some text similarity with anchor OR same dup group
                    a = g.at[i, "text_norm"]
                    b = g.at[j, "text_norm"]
                    same_dup = g.at[i, "dup_group_id"] == g.at[j, "dup_group_id"]
                    sim = token_set_ratio(a, b) / 100.0 if a and b else 0.0
                    if same_dup or sim >= 0.4 or len(group_idx) < 3:
                        group_idx.append(j)
                        visited[j] = True
            inc_counter += 1
            inc_id = f"INC{inc_counter:05d}"
            sub = g.loc[group_idx]
            unique_count = sub["dup_group_id"].nunique()
            top_evidence = sub.sort_values("confidence_issue", ascending=False)["text_norm"].head(3).tolist()
            incidents.append({
                "incident_id": inc_id,
                "store_id": store,
                "region": sub["region"].iloc[0],
                "issue_category": cat,
                "severity": sub["severity"].mode().iloc[0] if len(sub["severity"].mode()) else "medium",
                "first_seen": sub["ts"].min(),
                "last_seen": sub["ts"].max(),
                "total_records": len(sub),
                "unique_record_count": int(unique_count),
                "channels": sorted(sub["channel"].unique().tolist()),
                "record_ids": sub["record_id"].tolist(),
                "evidence_snippets": top_evidence,
                "max_confidence": float(sub["confidence_issue"].max()),
                "needs_human_review": bool(sub["needs_human_review"].any()),
            })

    inc_df = pd.DataFrame(incidents)
    inc_df.to_parquet(PROC / "incidents.parquet", index=False)
    df.to_parquet(PROC / "classified.parquet", index=False)
    print(f"[fusion] {len(inc_df)} incidents formed")
    print(f"[fusion] multi-channel incidents: {(inc_df['channels'].map(len) > 1).sum()}")


if __name__ == "__main__":
    run()
