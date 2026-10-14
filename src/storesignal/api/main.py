"""FastAPI service exposing the pipeline outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from storesignal.config import ROOT

PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

API_KEY = "demo-key-storesignal"

app = FastAPI(title="StoreSignal AI", version="1.0.0")


def check_key(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/")
def root():
    return {"service": "StoreSignal AI", "status": "ok"}


@app.get("/incidents")
def incidents(region: str | None = None, store_id: str | None = None, limit: int = 100, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    df = pd.read_parquet(PROC / "incidents.parquet")
    if region:
        df = df[df["region"] == region]
    if store_id:
        df = df[df["store_id"] == store_id]
    df = df.head(limit)
    return df.drop(columns=["evidence_snippets"]).to_dict(orient="records")


@app.get("/alerts")
def alerts(region: str | None = None, limit: int = 100, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    df = pd.read_parquet(PROC / "alerts.parquet")
    if region:
        df = df[df["region"] == region]
    df = df.head(limit)
    return df.to_dict(orient="records")


@app.get("/alerts/{alert_id}")
def alert_detail(alert_id: str, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    df = pd.read_parquet(PROC / "alerts.parquet")
    row = df[df["alert_id"] == alert_id]
    if row.empty:
        raise HTTPException(404, "alert not found")
    return row.iloc[0].to_dict()


@app.get("/metrics")
def metrics(x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    with (REPORTS / "evaluation.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/replay/{incident_id}")
def replay(incident_id: str, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    with (PROC / "replay.json").open(encoding="utf-8") as fh:
        data = json.load(fh)
    if incident_id not in data:
        raise HTTPException(404, "incident not found")
    return data[incident_id]


@app.get("/brief/{region}")
def brief(region: str, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    path = REPORTS / f"brief_{region.replace(' ', '_')}.md"
    if not path.exists():
        raise HTTPException(404, "brief not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.post("/reset")
def reset(x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    return {"status": "reset endpoint available; use scripts/reset_demo.py"}


from pydantic import BaseModel


class FeedbackSubmission(BaseModel):
    alert_id: str
    label: str
    reviewer_id: str
    note: str = ""


class TransitionSubmission(BaseModel):
    incident_id: str
    stage: str
    owner: str = ""
    note: str = ""


@app.post("/alerts/{alert_id}/feedback")
def submit_feedback(alert_id: str, body: FeedbackSubmission, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    from storesignal.feedback.loop import submit
    return submit(alert_id, body.label, body.reviewer_id, body.note)


@app.get("/feedback/summary")
def feedback_summary(x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    from storesignal.feedback.loop import summary
    return summary()


@app.post("/incidents/{incident_id}/transition")
def transition_incident(incident_id: str, body: TransitionSubmission, x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    from storesignal.tracking.tracker import transition
    return transition(incident_id, body.stage, body.owner, body.note)


@app.get("/tracking/dashboard")
def tracking_dashboard(x_api_key: str | None = Header(None)):
    check_key(x_api_key)
    from storesignal.tracking.tracker import dashboard
    return dashboard()
