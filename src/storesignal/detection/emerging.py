"""Module C - Emerging-issue detection using rolling robust z-score on smoothed counts."""

from __future__ import annotations

import numpy as np
import pandas as pd

from storesignal.config import ROOT, load_thresholds

PROC = ROOT / "data" / "processed"
REF = ROOT / "data" / "reference"
SMOOTH_DAYS = 14  # rolling window to aggregate sparse signals


def run() -> None:
    cfg = load_thresholds().detection
    df = pd.read_parquet(PROC / "classified.parquet")
    stores = pd.read_csv(REF / "store_master.csv", dtype={"store_id": str})

    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["ts"].dt.floor("D")

    raw_counts = (
        df.groupby(["store_id", "issue_category", "date"])
        .size().reset_index(name="count")
    )

    exposure_col = cfg.exposure_field if cfg.exposure_field in stores.columns else None

    results = []
    for (store, cat), g in raw_counts.groupby(["store_id", "issue_category"]):
        g = g.sort_values("date").set_index("date")
        full_idx = pd.date_range(g.index.min(), g.index.max(), freq="D", tz="UTC")
        daily = g["count"].reindex(full_idx, fill_value=0)

        # Smoothed signal: rolling SMOOTH_DAYS sum
        smoothed = daily.rolling(SMOOTH_DAYS, min_periods=SMOOTH_DAYS).sum()

        proxy_used = exposure_col is None
        for i, (d, raw_val) in enumerate(daily.items()):
            val = float(smoothed.iloc[i])
            if i < cfg.min_periods:
                results.append({
                    "store_id": store, "issue_category": cat, "date": d,
                    "count": int(raw_val), "smoothed_count": val,
                    "baseline_median": np.nan, "z": np.nan,
                    "rate_ratio": np.nan, "flagged": False, "proxy_used": proxy_used,
                })
                continue

            hist = smoothed.iloc[max(0, i - cfg.window_days): i]
            if len(hist) < cfg.min_periods:
                results.append({
                    "store_id": store, "issue_category": cat, "date": d,
                    "count": int(raw_val), "smoothed_count": val,
                    "baseline_median": np.nan, "z": np.nan,
                    "rate_ratio": np.nan, "flagged": False, "proxy_used": proxy_used,
                })
                continue

            med = float(np.median(hist))
            if cfg.use_robust_z:
                mad = float(np.median(np.abs(hist - med)))
                scale = mad if mad > 1e-9 else 1.0
                z = 0.6745 * (val - med) / scale
            else:
                mu = float(hist.mean())
                sd = float(hist.std(ddof=0))
                scale = sd if sd > 1e-9 else 1.0
                z = (val - mu) / scale

            denom = med if med > 1e-9 else 0.5
            rate_ratio = val / denom

            flagged = (
                z >= cfg.z_threshold
                and val >= cfg.min_count
                and rate_ratio >= cfg.min_rate_increase
            )

            results.append({
                "store_id": store, "issue_category": cat, "date": d,
                "count": int(raw_val), "smoothed_count": val,
                "baseline_median": med, "z": float(z),
                "rate_ratio": float(rate_ratio),
                "flagged": bool(flagged), "proxy_used": proxy_used,
            })

    out = pd.DataFrame(results)
    out.to_parquet(PROC / "detections.parquet", index=False)
    flagged = out[out["flagged"]]
    print(f"[detect] {len(out)} store-category-days scored, {len(flagged)} flagged")

    # Check seeded incidents
    import yaml
    with (ROOT / "data" / "eval" / "seeded_incidents.yaml").open(encoding="utf-8") as fh:
        seeded = yaml.safe_load(fh)["incidents"]
    for inc in seeded:
        sub = flagged[(flagged["store_id"] == inc["store_id"]) & (flagged["issue_category"] == inc["category"])]
        if sub.empty:
            print(f"[detect] SEEDED {inc['id']}: NOT detected")
        else:
            first = sub["date"].min().date()
            print(f"[detect] SEEDED {inc['id']}: first flag {first}")


if __name__ == "__main__":
    run()
