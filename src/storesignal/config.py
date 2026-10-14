"""Configuration loader with Pydantic validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


class IngestionConfig(BaseModel):
    min_text_length: int = 3
    max_text_length: int = 5000
    near_dup_threshold: float = 0.95
    pii_redaction: bool = True


class ClassificationConfig(BaseModel):
    min_confidence_issue: float = 0.55
    min_confidence_severity: float = 0.60
    min_confidence_actionability: float = 0.60
    review_queue_enabled: bool = True


class DetectionConfig(BaseModel):
    window_days: int = 28
    min_periods: int = 14
    z_threshold: float = 3.0
    min_count: int = 2
    min_rate_increase: float = 2.0
    use_robust_z: bool = True
    exposure_field: str = "transactions_30d"
    proxy_allowed: bool = True


class FusionConfig(BaseModel):
    time_window_hours: int = 72
    similarity_threshold: float = 0.82


class BriefConfig(BaseModel):
    top_n: int = 5


class Thresholds(BaseModel):
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    brief: BriefConfig = Field(default_factory=BriefConfig)


class RiskRule(BaseModel):
    category: str
    route_to: str
    sla_hours: int


class RiskPolicy(BaseModel):
    policy_version: str = "1.0"
    rules: list[RiskRule] = Field(default_factory=list)


class RouteEntry(BaseModel):
    owner: str
    first_action: str
    sla_hours: int


class RoutingConfig(BaseModel):
    default_sla_hours: int = 48
    routes: dict[str, RouteEntry] = Field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=None)
def load_thresholds() -> Thresholds:
    return Thresholds.model_validate(_read_yaml(CONFIG_DIR / "thresholds.yaml"))


@lru_cache(maxsize=None)
def load_risk_policy() -> RiskPolicy:
    return RiskPolicy.model_validate(_read_yaml(CONFIG_DIR / "risk_policy.yaml"))


@lru_cache(maxsize=None)
def load_routing() -> RoutingConfig:
    return RoutingConfig.model_validate(_read_yaml(CONFIG_DIR / "routing.yaml"))
