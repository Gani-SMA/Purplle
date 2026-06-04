"""
app/models.py — Pydantic v2 models for every request / response shape.
Field names, types, and nullability are locked to the TRD event schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Event types (locked catalogue — 8 types)
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    ENTRY                  = "ENTRY"
    EXIT                   = "EXIT"
    ZONE_ENTER             = "ZONE_ENTER"
    ZONE_EXIT              = "ZONE_EXIT"
    ZONE_DWELL             = "ZONE_DWELL"
    BILLING_QUEUE_JOIN     = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON  = "BILLING_QUEUE_ABANDON"
    REENTRY                = "REENTRY"


# ---------------------------------------------------------------------------
# Ingest — request
# ---------------------------------------------------------------------------

class EventMetadata(BaseModel):
    queue_depth: int | None = None
    sku_zone:    str | None = None
    session_seq: int        = 0


class StoreEvent(BaseModel):
    """Locked event schema from TRD §2.3"""
    event_id:   UUID4      = Field(default_factory=uuid.uuid4)
    store_id:   str        = Field(..., max_length=50)
    camera_id:  str        = Field(..., max_length=50)
    visitor_id: str        = Field(..., max_length=50)
    event_type: EventType
    timestamp:  datetime
    zone_id:    str | None = Field(default=None, max_length=50)
    dwell_ms:   int        = Field(default=0, ge=0)
    is_staff:   bool       = False
    confidence: float      = Field(..., ge=0.0, le=1.0)
    metadata:   EventMetadata = Field(default_factory=EventMetadata)

    @field_validator("zone_id")
    @classmethod
    def zone_required_for_zone_events(cls, v: str | None, info: Any) -> str | None:
        # zone_id must be non-null for zone-related events
        return v

    @model_validator(mode="after")
    def check_zone_presence(self) -> "StoreEvent":
        zone_events = {
            EventType.ZONE_ENTER,
            EventType.ZONE_EXIT,
            EventType.ZONE_DWELL,
            EventType.BILLING_QUEUE_JOIN,
            EventType.BILLING_QUEUE_ABANDON,
        }
        if self.event_type in zone_events and not self.zone_id:
            raise ValueError(
                f"zone_id is required for event_type={self.event_type.value}"
            )
        return self


class IngestRequest(BaseModel):
    events: list[StoreEvent] = Field(..., max_length=500)


# ---------------------------------------------------------------------------
# Ingest — response
# ---------------------------------------------------------------------------

class IngestError(BaseModel):
    event_id: str
    reason:   str


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors:   list[IngestError] = []


# ---------------------------------------------------------------------------
# GET /stores/{id}/metrics
# ---------------------------------------------------------------------------

class ZoneDwell(BaseModel):
    zone_id:      str
    avg_dwell_ms: float


class MetricsResponse(BaseModel):
    store_id:          str
    unique_visitors:   int
    conversion_rate:   float          # 0.0 – 1.0
    avg_dwell_by_zone: list[ZoneDwell]
    queue_depth:       int
    abandonment_rate:  float          # 0.0 – 1.0


# ---------------------------------------------------------------------------
# GET /stores/{id}/funnel
# ---------------------------------------------------------------------------

class FunnelStage(BaseModel):
    stage:        str
    count:        int
    drop_off_pct: float   # 0.0 – 100.0; 0 for first stage


class FunnelResponse(BaseModel):
    store_id: str
    stages:   list[FunnelStage]


# ---------------------------------------------------------------------------
# GET /stores/{id}/heatmap
# ---------------------------------------------------------------------------

class HeatmapZone(BaseModel):
    zone_id:        str
    visit_count:    int
    avg_dwell_ms:   float
    normalised_score: float   # 0–100


class HeatmapResponse(BaseModel):
    store_id:        str
    zones:           list[HeatmapZone]
    data_confidence: bool   # False if <20 sessions today


# ---------------------------------------------------------------------------
# GET /stores/{id}/anomalies
# ---------------------------------------------------------------------------

class AnomalySeverity(str, Enum):
    INFO     = "INFO"
    WARN     = "WARN"
    CRITICAL = "CRITICAL"


class AnomalyItem(BaseModel):
    anomaly_type:     str
    severity:         AnomalySeverity
    message:          str
    suggested_action: str
    detected_at:      datetime


class AnomalyResponse(BaseModel):
    store_id:  str
    anomalies: list[AnomalyItem]


# ---------------------------------------------------------------------------
# GET /health  (already partly in main.py — now standardised here)
# ---------------------------------------------------------------------------

class StoreHealthItem(BaseModel):
    store_id:       str
    last_event_ts:  str | None
    lag_minutes:    float | None
    status:         str   # "live" | "stale"


class HealthResponse(BaseModel):
    status:  str           # "healthy" | "stale"
    stores:  list[StoreHealthItem]


# ---------------------------------------------------------------------------
# POS Ingest
# ---------------------------------------------------------------------------

class PosTransaction(BaseModel):
    transaction_id:   str
    store_id:         str
    timestamp:        datetime
    basket_value_inr: float


class PosIngestRequest(BaseModel):
    transactions: list[PosTransaction] = Field(..., max_length=1000)


class PosIngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors:   list[str] = []


# ---------------------------------------------------------------------------
# GET /stores/{id}/events/recent
# ---------------------------------------------------------------------------

class RecentEventItem(BaseModel):
    event_id:   str
    event_type: str
    visitor_id: str
    camera_id:  str
    zone_id:    str | None
    timestamp:  datetime
    is_staff:   bool
    confidence: float
    dwell_ms:   int


class RecentEventsResponse(BaseModel):
    store_id: str
    events:   list[RecentEventItem]
    total:    int


# ---------------------------------------------------------------------------
# GET /stores/{id}/cameras
# ---------------------------------------------------------------------------

class CameraStatusItem(BaseModel):
    camera_id:        str
    last_seen_ts:     str | None
    event_count_today: int
    lag_seconds:      float | None
    status:           str   # "live" | "stale" | "unknown"


class CameraStatusResponse(BaseModel):
    store_id: str
    cameras:  list[CameraStatusItem]


# ---------------------------------------------------------------------------
# GET /stores/{id}/visitors/{visitor_id}/journey  (option B)
# ---------------------------------------------------------------------------

class VisitorJourneyEvent(BaseModel):
    event_type: str
    zone_id:    str | None
    timestamp:  datetime
    dwell_ms:   int
    camera_id:  str


class VisitorJourneyResponse(BaseModel):
    store_id:   str
    visitor_id: str
    is_staff:   bool
    events:     list[VisitorJourneyEvent]
    total_dwell_ms: int
    zones_visited:  list[str]


# ---------------------------------------------------------------------------
# GET /stores/{id}/pos/summary  (option C)
# ---------------------------------------------------------------------------

class PosSummaryResponse(BaseModel):
    store_id:             str
    total_transactions:   int
    total_revenue_inr:    float
    avg_basket_inr:       float
    revenue_per_visitor:  float
    hourly_revenue:       list[dict]   # [{hour: int, revenue: float, transactions: int}]
