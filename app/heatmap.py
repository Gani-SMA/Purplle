"""
app/heatmap.py — Zone visit frequency + avg dwell, normalised 0–100.
data_confidence = False if fewer than 20 sessions today.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import HeatmapResponse, HeatmapZone

logger = structlog.get_logger("heatmap")

_TODAY_SQL = "(SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events)"


async def compute_heatmap(store_id: str, db: AsyncSession) -> HeatmapResponse:
    # ── Get today's start timestamp ───────────────────────────────────────────
    res = await db.execute(text(
        "SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events"
    ))
    today_start = res.scalar()

    # Zone visit counts + average dwell
    rows = await db.execute(text("""
        SELECT zone_id,
               COUNT(*)          AS visit_count,
               AVG(dwell_ms)     AS avg_dwell_ms
        FROM events
        WHERE store_id  = :sid
          AND is_staff  = false
          AND event_type = 'ZONE_ENTER'
          AND zone_id   IS NOT NULL
          AND timestamp >= :today_start
        GROUP BY zone_id
        ORDER BY visit_count DESC
    """), {"sid": store_id, "today_start": today_start})
    raw = rows.fetchall()   # [(zone_id, count, avg_dwell), ...]

    # Total sessions today (for data_confidence)
    sc = await db.execute(text("""
        SELECT COUNT(*)
        FROM sessions
        WHERE store_id = :sid
          AND entry_ts >= :today_start
    """), {"sid": store_id, "today_start": today_start})
    total_sessions: int = sc.scalar() or 0
    data_confidence: bool = total_sessions >= 20

    if not raw:
        return HeatmapResponse(store_id=store_id, zones=[], data_confidence=data_confidence)

    max_visits = max(r[1] for r in raw) or 1

    zones = [
        HeatmapZone(
            zone_id=r[0],
            visit_count=r[1],
            avg_dwell_ms=round(r[2] or 0.0, 2),
            normalised_score=round(r[1] / max_visits * 100, 2),
        )
        for r in raw
    ]

    logger.info("heatmap_computed", store_id=store_id, zone_count=len(zones), data_confidence=data_confidence)
    return HeatmapResponse(store_id=store_id, zones=zones, data_confidence=data_confidence)
