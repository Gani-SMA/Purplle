"""
app/anomalies.py — Three anomaly detection rules (from locked TRD):

  QUEUE_SPIKE     (CRITICAL) — queue_depth > QUEUE_SPIKE_THRESHOLD
  CONVERSION_DROP (WARN)     — today rate < 7-day avg × (1 - threshold%)
  DEAD_ZONE       (INFO)     — no ZONE_ENTER in any zone for DEAD_ZONE_MIN minutes
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import AnomalyItem, AnomalyResponse, AnomalySeverity

logger = structlog.get_logger("anomalies")

QUEUE_SPIKE_THRESHOLD        = int(os.getenv("QUEUE_SPIKE_THRESHOLD",        "5"))
CONVERSION_DROP_THRESHOLD_PCT= float(os.getenv("CONVERSION_DROP_THRESHOLD_PCT","20"))
DEAD_ZONE_MIN                = int(os.getenv("DEAD_ZONE_MIN",                "30"))

_TODAY_SQL  = "(SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events)"
_7DAYS_SQL  = "(now() AT TIME ZONE 'UTC' - INTERVAL '7 days')"


async def compute_anomalies(
    store_id: str,
    db: AsyncSession,
    redis,
) -> AnomalyResponse:
    # ── Get today's start timestamp ───────────────────────────────────────────
    res = await db.execute(text(
        "SELECT COALESCE(date_trunc('day', MAX(timestamp)), date_trunc('day', now() AT TIME ZONE 'UTC')) FROM events"
    ))
    today_start = res.scalar()

    anomalies: list[AnomalyItem] = []
    now = datetime.now(timezone.utc)

    # ── 1. QUEUE_SPIKE ────────────────────────────────────────────────────────
    qdepth_raw = await redis.get(f"queue_depth:{store_id}")
    queue_depth = int(qdepth_raw) if qdepth_raw else 0
    if queue_depth > QUEUE_SPIKE_THRESHOLD:
        anomalies.append(AnomalyItem(
            anomaly_type="QUEUE_SPIKE",
            severity=AnomalySeverity.CRITICAL,
            message=f"Billing queue depth is {queue_depth} — exceeds threshold of {QUEUE_SPIKE_THRESHOLD}.",
            suggested_action="Open an additional billing counter immediately.",
            detected_at=now,
        ))

    # ── 2. CONVERSION_DROP ────────────────────────────────────────────────────
    today_row = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE is_converted = true) AS conv,
            COUNT(*)                                     AS total
        FROM sessions
        WHERE store_id = :sid AND entry_ts >= :today_start
    """), {"sid": store_id, "today_start": today_start})
    tr = today_row.fetchone()
    today_conv  = tr[0] or 0
    today_total = tr[1] or 0
    today_rate  = today_conv / today_total if today_total else 0.0

    week_row = await db.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE is_converted = true) AS conv,
            COUNT(*)                                     AS total
        FROM sessions
        WHERE store_id = :sid
          AND entry_ts >= {_7DAYS_SQL}
          AND entry_ts <  :today_start
    """), {"sid": store_id, "today_start": today_start})
    wr = week_row.fetchone()
    week_conv  = wr[0] or 0
    week_total = wr[1] or 0
    week_rate  = week_conv / week_total if week_total else 0.0

    threshold_rate = week_rate * (1 - CONVERSION_DROP_THRESHOLD_PCT / 100)
    if week_total > 0 and today_total > 0 and today_rate < threshold_rate:
        anomalies.append(AnomalyItem(
            anomaly_type="CONVERSION_DROP",
            severity=AnomalySeverity.WARN,
            message=(
                f"Today's conversion rate ({today_rate:.1%}) is more than "
                f"{CONVERSION_DROP_THRESHOLD_PCT:.0f}% below the 7-day average ({week_rate:.1%})."
            ),
            suggested_action="Review ongoing promotions and staff engagement strategy.",
            detected_at=now,
        ))

    # ── 3. DEAD_ZONE ──────────────────────────────────────────────────────────
    cutoff = now - timedelta(minutes=DEAD_ZONE_MIN)
    dz_row = await db.execute(text("""
        SELECT COUNT(*)
        FROM events
        WHERE store_id  = :sid
          AND is_staff  = false
          AND event_type = 'ZONE_ENTER'
          AND timestamp >= :cutoff
    """), {"sid": store_id, "cutoff": cutoff})
    zone_events_recent = dz_row.scalar() or 0

    # Only flag if the store has had *some* activity today (avoid false positives on brand-new stores)
    has_today_activity = await db.execute(text("""
        SELECT COUNT(*) FROM events WHERE store_id = :sid AND timestamp >= :today_start
    """), {"sid": store_id, "today_start": today_start})
    if (has_today_activity.scalar() or 0) > 0 and zone_events_recent == 0:
        anomalies.append(AnomalyItem(
            anomaly_type="DEAD_ZONE",
            severity=AnomalySeverity.INFO,
            message=f"No zone entry events recorded in any zone for the past {DEAD_ZONE_MIN} minutes.",
            suggested_action="Review zone product placement, lighting, and in-store signage.",
            detected_at=now,
        ))

    logger.info("anomalies_computed", store_id=store_id, count=len(anomalies))
    return AnomalyResponse(store_id=store_id, anomalies=anomalies)
