"""
app/metrics.py — Compute /stores/{id}/metrics from PostgreSQL + Redis.
All values are zero-safe: never return null, never 5xx on empty store.
"""
from __future__ import annotations

import os

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import MetricsResponse, ZoneDwell

logger = structlog.get_logger("metrics")

_TODAY_SQL = "(SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events)"


async def compute_metrics(
    store_id: str,
    db: AsyncSession,
    redis,
) -> MetricsResponse:
    # ── Get today's start timestamp ───────────────────────────────────────────
    res = await db.execute(text(
        "SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events"
    ))
    today_start = res.scalar()

    # ── Unique customer visitors today ────────────────────────────────────────
    uv_row = await db.execute(text("""
        SELECT COUNT(DISTINCT visitor_id)
        FROM events
        WHERE store_id = :sid
          AND is_staff = false
          AND timestamp >= :today_start
          AND event_type IN ('ENTRY','REENTRY')
    """), {"sid": store_id, "today_start": today_start})
    unique_visitors: int = uv_row.scalar() or 0

    # ── Conversion rate (POS-correlated sessions) ─────────────────────────────
    conv_row = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE is_converted = true)  AS converted,
            COUNT(*)                                      AS total
        FROM sessions
        WHERE store_id = :sid
          AND entry_ts >= :today_start
    """), {"sid": store_id, "today_start": today_start})
    cr = conv_row.fetchone()
    converted = cr[0] or 0
    total_sessions = cr[1] or 0
    conversion_rate = round(converted / total_sessions, 4) if total_sessions else 0.0

    # ── Avg dwell per zone ────────────────────────────────────────────────────
    dwell_rows = await db.execute(text("""
        SELECT zone_id, AVG(dwell_ms)
        FROM events
        WHERE store_id  = :sid
          AND is_staff  = false
          AND zone_id   IS NOT NULL
          AND dwell_ms  > 0
          AND timestamp >= :today_start
        GROUP BY zone_id
        ORDER BY zone_id
    """), {"sid": store_id, "today_start": today_start})
    avg_dwell_by_zone = [
        ZoneDwell(zone_id=row[0], avg_dwell_ms=round(row[1] or 0.0, 2))
        for row in dwell_rows.fetchall()
    ]

    # ── Live queue depth from Redis ───────────────────────────────────────────
    qdepth_raw = await redis.get(f"queue_depth:{store_id}")
    queue_depth = max(0, int(qdepth_raw)) if qdepth_raw else 0

    # ── Abandonment rate ──────────────────────────────────────────────────────
    aband_row = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE abandoned_queue = true)  AS abandoned,
            COUNT(*) FILTER (WHERE reached_billing = true)  AS reached
        FROM sessions
        WHERE store_id = :sid
          AND entry_ts >= :today_start
    """), {"sid": store_id, "today_start": today_start})
    ar = aband_row.fetchone()
    abandoned = ar[0] or 0
    reached   = ar[1] or 0
    abandonment_rate = round(abandoned / reached, 4) if reached else 0.0

    logger.info(
        "metrics_computed",
        store_id=store_id,
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        queue_depth=queue_depth,
    )

    return MetricsResponse(
        store_id=store_id,
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        avg_dwell_by_zone=avg_dwell_by_zone,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate,
    )
