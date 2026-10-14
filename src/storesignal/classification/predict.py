"""Module B - Apply trained classifier to unified records."""

from __future__ import annotations

import csv
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from storesignal.config import ROOT, load_thresholds, load_routing


REF = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"


def load_taxonomy() -> list[dict]:
    with (REF / "taxonomy.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def owner_for(category: str, taxonomy: list[dict], routing) -> str:
    if category in routing.routes:
        return routing.routes[category].owner
    for r in taxonomy:
        if r["id"] == category:
            return r["owner"]
    return "Store Ops"


def run() -> None:
    cfg = load_thresholds().classification
    routing = load_routing()
    taxonomy = load_taxonomy()

    bundle = joblib.load(MODELS / "baseline.joblib")
    df = pd.read_parquet(PROC / "unified.parquet")

    texts = df["text_norm"].tolist()

    Xc = bundle["vec_cat"].transform(texts)
    probs_c = bundle["clf_cat"].predict_proba(Xc)
    cats = bundle["clf_cat"].classes_
    idx = probs_c.argmax(axis=1)
    df["issue_categories"] = [ [cats[i]] for i in idx ]
    df["confidence_issue"] = probs_c.max(axis=1)

    Xs = bundle["vec_sev"].transform(texts)
    probs_s = bundle["clf_sev"].predict_proba(Xs)
    sevs = bundle["clf_sev"].classes_
    sidx = probs_s.argmax(axis=1)
    df["severity"] = [sevs[i] for i in sidx]
    df["confidence_severity"] = probs_s.max(axis=1)

    Xa = bundle["vec_act"].transform(texts)
    probs_a = bundle["clf_act"].predict_proba(Xa)
    aidx = probs_a.argmax(axis=1)
    df["actionable"] = aidx == 1
    df["confidence_actionability"] = probs_a.max(axis=1)

    needs_review = (
        (df["confidence_issue"] < cfg.min_confidence_issue)
        | (df["confidence_severity"] < cfg.min_confidence_severity)
        | (df["confidence_actionability"] < cfg.min_confidence_actionability)
    )
    df["needs_human_review"] = needs_review

    df["issue_category"] = df["issue_categories"].map(lambda c: c[0] if c else "other")
    df["owning_function"] = df["issue_category"].map(lambda c: owner_for(c, taxonomy, routing))
    df["model_version"] = "baseline-tfidf-lr-v1"

    df.to_parquet(PROC / "classified.parquet", index=False)
    print(f"[predict] wrote {PROC / 'classified.parquet'} ({len(df)} rows)")
    print(f"[predict] review queue: {int(needs_review.sum())} records")
    print(f"[predict] sample categories: {df['issue_category'].value_counts().head(8).to_dict()}")


if __name__ == "__main__":
    run()
