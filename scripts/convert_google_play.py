"""Convert Google Play India reviews into StoreSignal AI schema.

This is a supplementary robustness dataset - it has no ground-truth labels,
no store IDs, no seeded incidents. We map apps to virtual stores, use the
star rating as a severity proxy, and let the classifier assign categories.

Primary evaluation remains on the synthetic R5-schema dataset.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "data" / "real"
RAW = ROOT / "data" / "raw_real"
EVAL = ROOT / "data" / "eval"

SEED = 20261015
ANCHOR = pd.Timestamp("2026-10-15", tz="UTC")

REGIONS = ["South", "North", "West", "East"]
CITIES = {
    "South": ["Bengaluru", "Hyderabad", "Chennai"],
    "North": ["Delhi", "Gurgaon", "Noida"],
    "West": ["Mumbai", "Pune"],
    "East": ["Kolkata"],
}

# Sample size cap to keep pipeline runtime reasonable
MAX_RECORDS = 20000

# Filler words that signal non-operational praise - we keep them but tag them
PRAISE_HINTS = ["best app", "love this app", "great app", "awesome app", "amazing app",
                "thanks for", "thank you", "superb app", "excellent app"]


def detect_language(text: str) -> str:
    """Simple heuristic: Devanagari script -> Hindi; known Hinglish markers -> hi-en."""
    t = text.lower()
    # Devanagari block
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    # Hinglish markers
    hinglish_markers = ["hai", "kya", "nahi", "nhi", "kaise", "bahut", "karo", "kyu",
                        "mera", "meri", "aap", "bhai", "accha", "thik", "bekar",
                        "bakwas", "paisa", "kitna", "kaisa", "aana", "jana"]
    hits = sum(1 for m in hinglish_markers if f" {m} " in f" {t} ")
    if hits >= 2:
        return "hi-en"
    # Tamil transliteration markers
    ta_markers = ["romba", "illa", "irukku", "vanakkam", "nalla", "mosam"]
    if sum(1 for m in ta_markers if f" {m} " in f" {t} ") >= 2:
        return "ta-translit"
    return "en"


def rating_to_severity_proxy(rating: int) -> str:
    """Map star rating to severity proxy. This is a proxy, not a label."""
    if rating <= 1:
        return "critical"
    if rating == 2:
        return "high"
    if rating == 3:
        return "medium"
    return "low"


def app_to_store_id(app_name: str) -> str:
    """Deterministic mapping from app name to a virtual store id."""
    h = int(hashlib.md5(app_name.encode("utf-8")).hexdigest()[:8], 16)
    return f"R{h % 20:03d}"


def make_virtual_store_master(apps: list[str]) -> pd.DataFrame:
    rows = []
    for app in sorted(set(apps)):
        sid = app_to_store_id(app)
        h = int(hashlib.md5(app.encode("utf-8")).hexdigest()[8:16], 16)
        region = REGIONS[h % 4]
        city = CITIES[region][(h // 4) % len(CITIES[region])]
        size_band = ["S", "M", "L", "XL"][(h // 8) % 4]
        rows.append({
            "store_id": sid,
            "store_name": app[:60],
            "region": region,
            "city": city,
            "size_band": size_band,
            "transactions_30d": 10000 + (h % 50000),
            "visits_30d": 15000 + (h % 70000),
            "opened_at": "2020-01-01",
        })
    return pd.DataFrame(rows).drop_duplicates("store_id").reset_index(drop=True)


def run() -> None:
    rng = random.Random(SEED)
    print("[convert] reading Google Play CSV...")
    df = pd.read_csv(REAL / "google_play_reviews.csv", low_memory=False)
    print(f"[convert] raw rows: {len(df):,}")

    # Fix column names with leading spaces
    df.columns = [c.strip() for c in df.columns]

    # Drop rows without review text
    df = df[df["Review"].notna()].copy()
    df["Review"] = df["Review"].astype(str).str.strip()
    df = df[df["Review"].str.len() >= 20]
    print(f"[convert] after text-length filter: {len(df):,}")

    # Focus on complaint-side: keep rating <= 3
    df = df[df["Rating"].between(1, 3)]
    print(f"[convert] after rating<=3 filter: {len(df):,}")

    # Cap size
    if len(df) > MAX_RECORDS:
        df = df.sample(n=MAX_RECORDS, random_state=SEED).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    print(f"[convert] final sample size: {len(df):,}")

    # Build timestamps
    df["ts_str"] = df["Date"].astype(str).str.strip() + " " + df["Time"].astype(str).str.strip()
    df["ts"] = pd.to_datetime(df["ts_str"], errors="coerce", utc=True)

    # Build records in R5 schema
    records = []
    for i, row in df.iterrows():
        rid = f"GP{i+1:07d}"
        store_id = app_to_store_id(str(row["App_Name"]))
        lang = detect_language(row["Review"])
        ts = row["ts"]
        if pd.isna(ts):
            ts = ANCHOR - pd.Timedelta(days=rng.randint(0, 90))

        records.append({
            "record_id": rid,
            "channel": "online_review",
            "text": row["Review"],
            "timestamp": ts.isoformat(),
            "store_id": store_id,
            "source_meta": {
                "app_name": str(row["App_Name"])[:80],
                "rating": int(row["Rating"]),
                "upvotes": int(row.get("Comment_Upvotes", 0) or 0),
            },
            "language_hint": lang,
            "_source": "google_play_india",
        })

    # Write channel file
    RAW.mkdir(parents=True, exist_ok=True)
    with (RAW / "google_play.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[convert] wrote {RAW / 'google_play.jsonl'} ({len(records)} records)")

    # Write virtual store master
    stores = make_virtual_store_master(df["App_Name"].astype(str).tolist())
    stores.to_csv(REAL / "store_master_real.csv", index=False)
    print(f"[convert] wrote {REAL / 'store_master_real.csv'} ({len(stores)} virtual stores)")

    # Language distribution
    lang_counts: dict[str, int] = {}
    for r in records:
        lang_counts[r["language_hint"]] = lang_counts.get(r["language_hint"], 0) + 1
    print(f"[convert] language distribution: {lang_counts}")


if __name__ == "__main__":
    run()
