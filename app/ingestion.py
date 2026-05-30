"""
app/ingestion.py — Batch event ingest logic.

Pipeline:
  1. Redis SETNX dedup:{event_id}  (7-day TTL)  — skip if already seen
  2. Batch INSERT INTO events ON CONFLICT DO NOTHING
  3. Upsert sessions on ENTRY / EXIT
  4. Update queue_depth:{store_id} on BILLING_QUEUE_JOIN / ABANDON
  5. Update stale_feed:{store_id}  (ISO timestamp)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import EventType, IngestError, IngestResponse, StoreEvent

logger = structlog.get_logger("ingestion")

_DEDUP_TTL_SEC   = 7 * 24 * 3600   # 7 days
_STALE_FEED_KEY  = "stale_feed:{store_id}"
_QUEUE_DEPTH_KEY = "queue_depth:{store_id}"


async def ingest_events(
    events: list[StoreEvent],
    session: AsyncSession,
    redis,
) -> IngestResponse:
    accepted = 0
    rejected = 0
    errors: list[IngestError] = []

    # ── 1. Redis dedup filter ────────────────────────────────────────────────
    new_events: list[StoreEvent] = []
    for ev in events:
        key = f"dedup:{ev.event_id}"
        was_set = await redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SEC)
        if was_set:
            new_events.append(ev)
        else:
            # already seen — idempotent skip, NOT an error
            logger.debug("event_deduplicated", event_id=str(ev.event_id))

    if not new_events:
        return IngestResponse(accepted=0, rejected=rejected, errors=errors)

    # ── 2. Batch INSERT events ───────────────────────────────────────────────
    rows = []
    for ev in new_events:
        rows.append({
            "event_id":    str(ev.event_id),
            "store_id":    ev.store_id,
            "camera_id":   ev.camera_id,
            "visitor_id":  ev.visitor_id,
            "event_type":  ev.event_type.value,
            "timestamp":   ev.timestamp,
            "zone_id":     ev.zone_id,
            "dwell_ms":    ev.dwell_ms,
            "is_staff":    ev.is_staff,
            "confidence":  ev.confidence,
            "queue_depth": ev.metadata.queue_depth,
            "sku_zone":    ev.metadata.sku_zone,
            "session_seq": ev.metadata.session_seq,
            "raw_metadata": json.dumps(ev.metadata.model_dump()),
        })

    insert_sql = text("""
        INSERT INTO events
          (event_id, store_id, camera_id, visitor_id, event_type,
           timestamp, zone_id, dwell_ms, is_staff, confidence,
           queue_depth, sku_zone, session_seq, raw_metadata)
        VALUES
          (CAST(:event_id AS uuid), :store_id, :camera_id, :visitor_id, :event_type,
           :timestamp, :zone_id, :dwell_ms, :is_staff, :confidence,
           :queue_depth, :sku_zone, :session_seq, CAST(:raw_metadata AS jsonb))
        ON CONFLICT (event_id) DO NOTHING
    """)

    try:
        await session.execute(insert_sql, rows)
    except Exception as exc:
        logger.error("batch_insert_failed", error=str(exc))
        for ev in new_events:
            errors.append(IngestError(event_id=str(ev.event_id), reason=str(exc)))
        rejected += len(new_events)
        return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)

    accepted += len(new_events)

    # ── 3. Session upsert (ENTRY opens, EXIT closes) ─────────────────────────
    for ev in new_events:
        if ev.is_staff:
            continue
        try:
            await _upsert_session(ev, session)
        except Exception as exc:
            logger.warning("session_upsert_failed", event_id=str(ev.event_id), error=str(exc))

    # ── 4. Redis queue depth updates ─────────────────────────────────────────
    for ev in new_events:
        if ev.event_type == EventType.BILLING_QUEUE_JOIN:
            await redis.incr(_QUEUE_DEPTH_KEY.format(store_id=ev.store_id))
        elif ev.event_type in (EventType.BILLING_QUEUE_ABANDON, EventType.EXIT):
            depth = await redis.get(_QUEUE_DEPTH_KEY.format(store_id=ev.store_id))
            if depth and int(depth) > 0:
                await redis.decr(_QUEUE_DEPTH_KEY.format(store_id=ev.store_id))

    # ── 5. Update stale_feed per store ───────────────────────────────────────
    stores_seen: set[str] = {ev.store_id for ev in new_events}
    now_iso = datetime.now(timezone.utc).isoformat()
    for store_id in stores_seen:
        await redis.set(_STALE_FEED_KEY.format(store_id=store_id), now_iso)

    await session.commit()

    logger.info(
        "ingest_complete",
        accepted=accepted,
        rejected=rejected,
        error_count=len(errors),
    )
    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)


async def _upsert_session(ev: StoreEvent, session: AsyncSession) -> None:
    """Open a session on ENTRY/REENTRY; close it on EXIT."""
    if ev.event_type in (EventType.ENTRY, EventType.REENTRY):
        is_reentry = ev.event_type == EventType.REENTRY
        await session.execute(text("""
            INSERT INTO sessions
              (store_id, visitor_id, entry_ts, is_reentry)
            VALUES
              (:store_id, :visitor_id, :entry_ts, :is_reentry)
            ON CONFLICT DO NOTHING
        """), {
            "store_id":   ev.store_id,
            "visitor_id": ev.visitor_id,
            "entry_ts":   ev.timestamp,
            "is_reentry": is_reentry,
        })

    elif ev.event_type == EventType.EXIT:
        # Close the most recent open session for this visitor
        await session.execute(text("""
            UPDATE sessions
            SET
                exit_ts        = :exit_ts,
                total_dwell_ms = EXTRACT(EPOCH FROM (:exit_ts - entry_ts)) * 1000
            WHERE
                store_id   = :store_id
                AND visitor_id = :visitor_id
                AND exit_ts IS NULL
        """), {
            "store_id":   ev.store_id,
            "visitor_id": ev.visitor_id,
            "exit_ts":    ev.timestamp,
        })

    elif ev.event_type == EventType.BILLING_QUEUE_JOIN:
        # Mark session as having reached billing
        await session.execute(text("""
            UPDATE sessions
            SET reached_billing = true
            WHERE store_id = :store_id AND visitor_id = :visitor_id AND exit_ts IS NULL
        """), {"store_id": ev.store_id, "visitor_id": ev.visitor_id})

    elif ev.event_type == EventType.BILLING_QUEUE_ABANDON:
        await session.execute(text("""
            UPDATE sessions
            SET abandoned_queue = true
            WHERE store_id = :store_id AND visitor_id = :visitor_id AND exit_ts IS NULL
        """), {"store_id": ev.store_id, "visitor_id": ev.visitor_id})
