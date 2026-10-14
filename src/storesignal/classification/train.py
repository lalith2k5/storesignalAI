"""Module B - Train baseline classifier: TF-IDF + logistic regression.

Labels are pseudo-labels derived from taxonomy keywords (see design doc:
"Seed keywords for baseline training"). Hidden labels are NEVER read here.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from storesignal.config import ROOT, load_thresholds


REF = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"


def load_taxonomy() -> list[dict]:
    with (REF / "taxonomy.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pseudo_label_category(text: str, taxonomy: list[dict]) -> str:
    t = text.lower()
    best, best_score = "other", 0
    for row in taxonomy:
        kws = row["keywords"].split()
        score = sum(1 for kw in kws if kw in t)
        if score > best_score:
            best_score = score
            best = row["id"]
    return best


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def build_features(texts: list[str]) -> TfidfVectorizer:
    return TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
        max_features=60000,
        lowercase=True,
    )


def train_multiclass(texts, labels, class_weight="balanced"):
    vec = build_features(texts)
    X = vec.fit_transform(texts)
    clf = LogisticRegression(max_iter=2000, class_weight=class_weight, n_jobs=-1, C=4.0)
    clf.fit(X, labels)
    return vec, clf


def run() -> None:
    cfg = load_thresholds().classification
    taxonomy = load_taxonomy()
    cat_severity_default = {r["id"]: r["severity_default"] for r in taxonomy}

    df = pd.read_parquet(PROC / "unified.parquet")
    df = df[df["text_norm"].str.len() > 0].reset_index(drop=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"[train] {len(df)} records after cleaning")

    # Pseudo-labels
    print("[train] building pseudo-labels from taxonomy keywords...")
    df["pseudo_category"] = df["text_norm"].map(lambda t: pseudo_label_category(t, taxonomy))
    df["pseudo_severity"] = df["pseudo_category"].map(lambda c: cat_severity_default.get(c, "medium"))
    df["pseudo_actionable"] = df["pseudo_severity"].map(lambda s: s in ("critical", "high"))

    # Time-aware split
    n = len(df)
    tr = int(n * 0.80)
    va = int(n * 0.90)
    train_df = df.iloc[:tr]
    val_df = df.iloc[tr:va]

    print(f"[train] train={len(train_df)} val={len(val_df)}")

    texts_tr = train_df["text_norm"].tolist()
    texts_va = val_df["text_norm"].tolist()

    # Category model
    print("[train] category model...")
    vec_c, clf_c = train_multiclass(texts_tr, train_df["pseudo_category"].tolist())
    y_va = val_df["pseudo_category"].tolist()
    y_pred = clf_c.predict(vec_c.transform(texts_va))
    f1_cat = f1_score(y_va, y_pred, average="macro", zero_division=0)
    print(f"[train] val macro-F1 (category, pseudo-labels): {f1_cat:.3f}")

    # Severity model
    print("[train] severity model...")
    vec_s, clf_s = train_multiclass(texts_tr, train_df["pseudo_severity"].tolist())

    # Actionability model
    print("[train] actionability model...")
    vec_a, clf_a = train_multiclass(texts_tr, train_df["pseudo_actionable"].astype(int).tolist())

    MODELS.mkdir(parents=True, exist_ok=True)
    bundle = {
        "vec_cat": vec_c, "clf_cat": clf_c,
        "vec_sev": vec_s, "clf_sev": clf_s,
        "vec_act": vec_a, "clf_act": clf_a,
    }
    model_path = MODELS / "baseline.joblib"
    joblib.dump(bundle, model_path)
    print(f"[train] saved {model_path}")

    data_hash = hash_file(PROC / "unified.parquet")
    card = {
        "model_version": "baseline-tfidf-lr-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_hash": data_hash,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "val_macro_f1_category_pseudo": float(f1_cat),
        "thresholds_issue": cfg.min_confidence_issue,
        "thresholds_severity": cfg.min_confidence_severity,
        "thresholds_actionability": cfg.min_confidence_actionability,
        "label_source": "taxonomy_keyword_pseudo_labels",
        "hidden_labels_used": False,
    }
    with (MODELS / "model_card.json").open("w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2)
    print(f"[train] wrote model card")


if __name__ == "__main__":
    run()
