"""Generate synthetic StoreSignal AI data: 4 channels, store master, hidden labels, seeded incidents.

This file exists only because the real 40k dataset has not yet been supplied.
Once the real data arrives, drop it in data/raw, data/reference, data/eval and do NOT run this.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
EVAL = ROOT / "data" / "eval"

SEED = 20261014
ANCHOR = datetime(2026, 10, 14, tzinfo=timezone.utc)

rng = random.Random(SEED)

# ---------- Load reference data ----------

def load_taxonomy() -> list[dict]:
    with (REF / "taxonomy.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_stores() -> list[dict]:
    with (REF / "store_master.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


TAXONOMY = load_taxonomy()
STORES = load_stores()
CATEGORY_IDS = [r["id"] for r in TAXONOMY if r["id"] != "other"]

# ---------- Template phrases per channel ----------
# Each template uses {cat} placeholder words chosen from the category keyword list.

EN_TEMPLATES = [
    "The {kw} at this store is really bad, please fix it.",
    "Very disappointed with the {kw} here.",
    "Not happy about the {kw}, will not return.",
    "Issue with {kw} today, staff did not help.",
    "The {kw} was unacceptable, please look into it.",
]

HINGLISH_TEMPLATES = [
    "Yahan ka {kw} bahut kharab hai, pls fix karo.",
    "{kw} ka problem hai, staff ne help nahi kiya.",
    "Aaj {kw} bahut kharab tha, nhi aaunga dobara.",
    "{kw} theek nahi hai, complaint karna chahta hu.",
]

TAMIL_TEMPLATES = [
    "Inga {kw} romba mosam, please paaru.",
    "{kw} problem irukku, staff help pannala.",
    "Innaiku {kw} romba bad, illa varamaaten.",
]

MARATHI_TEMPLATES = [
    "Ithe {kw} khup vaait aahe, please bagha.",
    "{kw} problem aahe, staff ne madad keli nahi.",
]

EMOJI_SUFFIX = ["", " 😡", " 😞", " 🤢", " 👎", " 😤", " 😠"]

TYPO_MAP = {
    "the": "teh",
    "please": "pls",
    "really": "realy",
    "problem": "prob",
    "store": "str",
    "not": "nt",
    "very": "vry",
}

CHANNELS = ["online_review", "inapp_comment", "staff_shift_note", "callcentre_transcript"]

CHANNEL_WEIGHTS = {
    "online_review": 0.40,
    "inapp_comment": 0.25,
    "staff_shift_note": 0.15,
    "callcentre_transcript": 0.20,
}


def make_text(category_id: str, language: str) -> str:
    tax = next(r for r in TAXONOMY if r["id"] == category_id)
    kws = tax["keywords"].split()
    kw = rng.choice(kws)

    if language == "en":
        tpl = rng.choice(EN_TEMPLATES)
    elif language == "hi-en":
        tpl = rng.choice(HINGLISH_TEMPLATES)
    elif language == "ta-translit":
        tpl = rng.choice(TAMIL_TEMPLATES)
    else:
        tpl = rng.choice(MARATHI_TEMPLATES)

    text = tpl.format(kw=kw)

    # Random typo
    if rng.random() < 0.10:
        for k, v in TYPO_MAP.items():
            if k in text:
                text = text.replace(k, v, 1)
                break

    # Random emoji
    text += rng.choice(EMOJI_SUFFIX)

    # Random truncation
    if rng.random() < 0.05:
        cut = rng.randint(8, max(9, len(text) - 3))
        text = text[:cut]

    return text


def random_language(channel: str) -> str:
    if channel == "callcentre_transcript":
        return rng.choices(["en", "hi-en", "ta-translit", "mr-translit"], [0.5, 0.3, 0.1, 0.1])[0]
    if channel == "staff_shift_note":
        return rng.choices(["en", "hi-en", "ta-translit", "mr-translit"], [0.6, 0.25, 0.1, 0.05])[0]
    return rng.choices(["en", "hi-en", "ta-translit", "mr-translit"], [0.65, 0.25, 0.07, 0.03])[0]


def random_timestamp(days_back_max: int = 90) -> str:
    days = rng.randint(0, days_back_max)
    secs = rng.randint(0, 86399)
    ts = ANCHOR - timedelta(days=days, seconds=secs)
    return ts.isoformat()


def weighted_category() -> str:
    """Non-uniform category distribution for realistic class imbalance."""
    weights = {
        "food_quality": 12, "refrigeration": 3, "stockout": 8, "app_crash": 5,
        "price_discrepancy": 4, "cleanliness": 6, "billing_error": 5,
        "staff_behavior": 6, "allergen_risk": 1, "hygiene": 2, "foreign_object": 1,
        "food_safety_other": 1, "staff_misconduct": 1, "wait_time": 7,
        "order_accuracy": 6, "packaging": 3, "delivery": 5, "menu_availability": 3,
        "portion_size": 3, "temperature_control": 3, "ambience": 2, "seating": 1,
        "parking": 1, "loyalty_program": 2, "app_ui": 2, "app_payment": 2,
        "order_cancellation": 2, "refund_issue": 3, "staff_shortage": 2,
        "equipment_failure": 3, "supplier_issue": 2, "other": 4,
    }
    cats = list(weights.keys())
    wts = [weights[c] for c in cats]
    return rng.choices(cats, wts)[0]


def severity_for(category_id: str) -> str:
    tax = next(r for r in TAXONOMY if r["id"] == category_id)
    if tax["policy_escalate"] == "true":
        return "critical"
    d = tax["severity_default"]
    return d


def actionability_for(category_id: str, severity: str) -> bool:
    if severity == "critical":
        return True
    if severity == "high":
        return rng.random() < 0.85
    if severity == "medium":
        return rng.random() < 0.60
    return rng.random() < 0.30


# ---------- Seeded incidents ----------
# Three planted incidents with a rising pattern over the last ~3 weeks.

SEEDED_INCIDENTS = [
    {
        "id": "INC-ALLERGEN-01",
        "store_id": "S007",
        "category": "allergen_risk",
        "channel_hint": "online_review",
        "days_ago_start": 20,
        "n_records": 9,
    },
    {
        "id": "INC-REFRIG-02",
        "store_id": "S014",
        "category": "refrigeration",
        "channel_hint": "staff_shift_note",
        "days_ago_start": 16,
        "n_records": 12,
    },
    {
        "id": "INC-HYGIENE-03",
        "store_id": "S018",
        "category": "hygiene",
        "channel_hint": "callcentre_transcript",
        "days_ago_start": 12,
        "n_records": 10,
    },
]


def generate_records(target_total: int = 40000) -> list[dict]:
    records: list[dict] = []
    per_channel = {
        ch: int(target_total * CHANNEL_WEIGHTS[ch]) for ch in CHANNELS
    }
    # Fix rounding
    diff = target_total - sum(per_channel.values())
    per_channel["online_review"] += diff

    record_counter = 0

    for channel, n in per_channel.items():
        for _ in range(n):
            store = rng.choice(STORES)
            category = weighted_category()
            language = random_language(channel)
            text = make_text(category, language)
            ts = random_timestamp()
            record_counter += 1
            rid = f"R{record_counter:07d}"

            rec = {
                "record_id": rid,
                "channel": channel,
                "text": text,
                "timestamp": ts,
                "store_id": store["store_id"],
                "source_meta": {},
                "language_hint": language,
                "_true_category": category,
            }

            if channel == "online_review":
                rec["source_meta"]["rating"] = rng.randint(1, 5)
            elif channel == "inapp_comment":
                rec["source_meta"]["rating"] = rng.randint(1, 5)
                rec["source_meta"]["app_version"] = rng.choice(["1.2.0", "1.3.1", "1.4.0"])
            elif channel == "staff_shift_note":
                rec["source_meta"]["shift"] = rng.choice(["morning", "evening", "night"])
                rec["source_meta"]["staff_role"] = rng.choice(["cashier", "kitchen", "floor"])
            elif channel == "callcentre_transcript":
                rec["source_meta"]["agent_id"] = f"A{rng.randint(100, 999)}"
                rec["source_meta"]["call_id"] = f"C{rng.randint(10000, 99999)}"
                rec["source_meta"]["duration_seconds"] = rng.randint(60, 900)

            records.append(rec)

    # ---------- Inject seeded incidents ----------
    for inc in SEEDED_INCIDENTS:
        for i in range(inc["n_records"]):
            # Rising pattern: most records in last few days
            day_offset = inc["days_ago_start"] - i * (inc["days_ago_start"] // inc["n_records"])
            ts = ANCHOR - timedelta(
                days=max(0, day_offset),
                seconds=rng.randint(0, 86399),
            )
            channel = rng.choice(CHANNELS)
            language = random_language(channel)
            text = make_text(inc["category"], language)
            record_counter += 1
            rid = f"R{record_counter:07d}"

            rec = {
                "record_id": rid,
                "channel": channel,
                "text": text,
                "timestamp": ts.isoformat(),
                "store_id": inc["store_id"],
                "source_meta": {},
                "language_hint": language,
                "_true_category": inc["category"],
                "_seeded_incident": inc["id"],
            }
            records.append(rec)

    rng.shuffle(records)
    return records


def write_channel_files(records: list[dict]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for channel in CHANNELS:
        path = RAW / f"{channel}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                if rec["channel"] != channel:
                    continue
                out = {k: v for k, v in rec.items() if not k.startswith("_")}
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        print(f"Wrote {path} ({sum(1 for r in records if r['channel'] == channel)} records)")


def write_hidden_labels(records: list[dict], sample_frac: float = 0.20) -> None:
    """Hidden labels are a random sample. Evaluation script reads them; nothing else does."""
    EVAL.mkdir(parents=True, exist_ok=True)
    sample_size = int(len(records) * sample_frac)
    sample = rng.sample(records, sample_size)

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.table({
            "record_id": [r["record_id"] for r in sample],
            "issue_category": [r["_true_category"] for r in sample],
            "severity": [severity_for(r["_true_category"]) for r in sample],
            "actionable": [actionability_for(r["_true_category"], severity_for(r["_true_category"])) for r in sample],
        })
        pq.write_table(table, EVAL / "hidden_labels.parquet")
        print(f"Wrote hidden labels ({sample_size} rows)")
    except ImportError:
        # Fallback: write CSV if pyarrow is unavailable
        with (EVAL / "hidden_labels.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["record_id", "issue_category", "severity", "actionable"])
            for r in sample:
                sev = severity_for(r["_true_category"])
                w.writerow([r["record_id"], r["_true_category"], sev, actionability_for(r["_true_category"], sev)])
        print(f"Wrote hidden labels CSV ({sample_size} rows)")


def write_seeded_incidents() -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    payload = {"incidents": SEEDED_INCIDENTS}
    with (EVAL / "seeded_incidents.yaml").open("w", encoding="utf-8") as fh:
        import yaml
        yaml.safe_dump(payload, fh, sort_keys=False)
    print(f"Wrote {EVAL / 'seeded_incidents.yaml'}")


def main() -> None:
    print(f"Generating synthetic data (seed={SEED})...")
    records = generate_records(40000)
    print(f"Generated {len(records)} total records")
    write_channel_files(records)
    write_hidden_labels(records)
    write_seeded_incidents()
    print("Done.")


if __name__ == "__main__":
    main()
