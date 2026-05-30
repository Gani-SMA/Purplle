"""
app/funnel.py — 4-stage conversion funnel.
Session unit: visitor counted once regardless of REENTRY events.
Drop-off % computed between consecutive stages.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import FunnelResponse, FunnelStage

logger = structlog.get_logger("funnel")

_TODAY_SQL = "date_trunc('day', now() AT TIME ZONE 'UTC')"


async def compute_funnel(store_id: str, db: AsyncSession) -> FunnelResponse:

    # Stage 1 — unique visitors (ENTRY or REENTRY, de-duped by visitor_id)
    s1 = await db.execute(text(f"""
        SELECT COUNT(DISTINCT visitor_id)
        FROM events
        WHERE store_id  = :sid
          AND is_staff  = false
          AND event_type IN ('ENTRY','REENTRY')
          AND timestamp >= {_TODAY_SQL}
    """), {"sid": store_id})
    entry_count: int = s1.scalar() or 0

    # Stage 2 — visited at least one zone
    s2 = await db.execute(text(f"""
        SELECT COUNT(DISTINCT visitor_id)
        FROM events
        WHERE store_id  = :sid
          AND is_staff  = false
          AND event_type = 'ZONE_ENTER'
          AND timestamp >= {_TODAY_SQL}
    """), {"sid": store_id})
    zone_count: int = s2.scalar() or 0

    # Stage 3 — reached billing zone (joined queue)
    s3 = await db.execute(text(f"""
        SELECT COUNT(DISTINCT visitor_id)
        FROM sessions
        WHERE store_id       = :sid
          AND reached_billing = true
          AND entry_ts       >= {_TODAY_SQL}
    """), {"sid": store_id})
    billing_count: int = s3.scalar() or 0

    # Stage 4 — converted (POS transaction matched)
    s4 = await db.execute(text(f"""
        SELECT COUNT(DISTINCT visitor_id)
        FROM sessions
        WHERE store_id    = :sid
          AND is_converted = true
          AND entry_ts    >= {_TODAY_SQL}
    """), {"sid": store_id})
    purchase_count: int = s4.scalar() or 0

    def drop_pct(prev: int, curr: int) -> float:
        if prev == 0:
            return 0.0
        return round((prev - curr) / prev * 100, 2)

    stages = [
        FunnelStage(stage="entry",        count=entry_count,    drop_off_pct=0.0),
        FunnelStage(stage="zone_visit",   count=zone_count,     drop_off_pct=drop_pct(entry_count,   zone_count)),
        FunnelStage(stage="billing_queue",count=billing_count,  drop_off_pct=drop_pct(zone_count,    billing_count)),
        FunnelStage(stage="purchase",     count=purchase_count, drop_off_pct=drop_pct(billing_count, purchase_count)),
    ]

    logger.info("funnel_computed", store_id=store_id, stages={s.stage: s.count for s in stages})
    return FunnelResponse(store_id=store_id, stages=stages)
