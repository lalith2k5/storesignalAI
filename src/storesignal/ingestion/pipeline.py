"""Module A - Ingestion and normalization.

Reads four channel JSONL files, applies quality flags and normalization,
joins store master, and writes a unified parquet.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from storesignal.config import load_thresholds, ROOT


CHANNELS = ["online_review", "inapp_comment", "staff_shift_note", "callcentre_transcript"]

RAW_DIR = ROOT / "data" / "raw"
REF_DIR = ROOT / "data" / "reference"
PROCESSED_DIR = ROOT / "data" / "processed"

# Emoji -> named token mapping. Keep sentiment-bearing symbols visible as tokens.
EMOJI_TOKENS = {
    "😡": " angry_face ", "😠": " angry_face ", "😤": " frustrated_face ",
    "😞": " sad_face ", "😢": " sad_face ", "🤢": " nauseated_face ",
    "🤮": " vomiting_face ", "👎": " thumbs_down ", "👍": " thumbs_up ",
    "😊": " smiling_face ", "🙂": " slight_smile ", "😐": " neutral_face ",
    "🔥": " fire ", "💩": " poop ", "🤬": " swearing_face ",
    "😑": " expressionless_face ", "😒": " unamused_face ", "🙄": " eye_roll ",
}

# Hinglish / transliterated abbreviations. Whole-token only.
ABBREVIATIONS = {
    "pls": "please", "plz": "please", "nhi": "nahi", "ni": "nahi",
    "hai": "hai", "tha": "tha", "kya": "kya", "ka": "ka",
    "romba": "romba", "illa": "illa", "irukku": "irukku",
    "khup": "khup", "aahe": "aahe", "nahi": "nahi",
    "prob": "problem", "str": "store", "nt": "not", "vry": "very",
    "teh": "the", "realy": "really", "kharab": "kharab",
}

# PII patterns. Redaction happens in text_norm, never in text_raw.
PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[GOVT_ID]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
]

URL_RE = re.compile(r"https?://\S+|www\.\S+")
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z]+")


def normalize_text(text: str, pii_redaction: bool) -> str:
    if not isinstance(text, str):
        return ""
    # 1. Unicode NFKC
    t = unicodedata.normalize("NFKC", text)
    # 2. Emoji -> tokens
    for emo, tok in EMOJI_TOKENS.items():
        t = t.replace(emo, tok)
    # 3. Remove URLs
    t = URL_RE.sub(" ", t)
    # 4. PII redaction
    if pii_redaction:
        for pat, repl in PII_PATTERNS:
            t = pat.sub(repl, t)
    # 5. Whole-token abbreviation expansion
    def repl_token(m: re.Match) -> str:
        w = m.group(0)
        return ABBREVIATIONS.get(w.lower(), w)
    t = TOKEN_RE.sub(repl_token, t)
    # 6. Collapse whitespace
    t = WHITESPACE_RE.sub(" ", t).strip()
    return t


def parse_timestamp(value: Any) -> tuple[datetime, bool]:
    if not isinstance(value, str) or not value:
        return datetime.now(timezone.utc), True
    try:
        s = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc), False
    except Exception:
        return datetime.now(timezone.utc), True


def load_store_master() -> pd.DataFrame:
    path = REF_DIR / "store_master.csv"
    return pd.read_csv(path, dtype={"store_id": str})


def read_channel(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def ingest() -> pd.DataFrame:
    cfg = load_thresholds().ingestion
    stores = load_store_master()
    known_stores = set(stores["store_id"])
    store_region = dict(zip(stores["store_id"], stores["region"]))

    all_rows: list[dict] = []
    seen_ids: set[str] = set()

    for channel in CHANNELS:
        path = RAW_DIR / f"{channel}.jsonl"
        if not path.exists():
            print(f"[ingest] channel file missing: {path}")
            continue
        raw_rows = read_channel(path)
        print(f"[ingest] {channel}: {len(raw_rows)} lines")
        for row in raw_rows:
            flags: list[str] = []
            rid = str(row.get("record_id", ""))
            if not rid:
                flags.append("missing_record_id")
                rid = f"missing_{len(all_rows)}"
            if rid in seen_ids:
                flags.append("duplicate_record_id")
            seen_ids.add(rid)

            text_raw = row.get("text", "") or ""
            if not isinstance(text_raw, str):
                text_raw = str(text_raw)
                flags.append("non_string_text")

            store_id = str(row.get("store_id", "")) or ""
            if store_id not in known_stores:
                flags.append("unknown_store")

            ts, ts_bad = parse_timestamp(row.get("timestamp"))
            if ts_bad:
                flags.append("malformed_ts")

            if len(text_raw.strip()) < cfg.min_text_length:
                flags.append("short_or_empty_text")

            text_norm = normalize_text(text_raw, cfg.pii_redaction)
            if any(p.sub("", text_raw) != p.sub("", text_norm) for p, _ in PII_PATTERNS):
                flags.append("pii_redacted")

            if len(text_norm) > cfg.max_text_length:
                text_norm = text_norm[: cfg.max_text_length]
                flags.append("truncated_for_embedding")

            all_rows.append({
                "record_id": rid,
                "channel": channel,
                "text_raw": text_raw,
                "text_norm": text_norm,
                "timestamp": ts,
                "store_id": store_id,
                "region": store_region.get(store_id, "Unknown"),
                "language_hint": row.get("language_hint", "unknown"),
                "quality_flags": flags,
            })

    df = pd.DataFrame(all_rows)
    # Flag near-duplicates within store-day buckets
    df = _flag_near_duplicates(df, cfg.near_dup_threshold)
    return df


def _flag_near_duplicates(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    try:
        from rapidfuzz.fuzz import token_set_ratio
    except ImportError:
        df["near_duplicate"] = False
        return df

    near_dup = [False] * len(df)
    if df.empty:
        df["near_duplicate"] = False
        return df

    df = df.reset_index(drop=True)
    df["_day"] = pd.to_datetime(df["timestamp"], utc=True).dt.date.astype(str)
    for (store, day), idx in df.groupby(["store_id", "_day"]).groups.items():
        sub = df.loc[list(idx)]
        if len(sub) < 2:
            continue
        texts = sub["text_norm"].tolist()
        positions = list(idx)
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if not texts[i] or not texts[j]:
                    continue
                score = token_set_ratio(texts[i], texts[j]) / 100.0
                if score >= threshold:
                    near_dup[positions[j]] = True
    df["near_duplicate"] = near_dup
    df = df.drop(columns=["_day"])
    return df


def write_unified(df: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "unified.parquet"
    df.to_parquet(out, index=False)
    print(f"[ingest] wrote {out} ({len(df)} rows)")
    return out


def run() -> None:
    df = ingest()
    write_unified(df)


if __name__ == "__main__":
    run()
