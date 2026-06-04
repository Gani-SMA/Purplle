"""
app/pos.py — POS transaction ingestion and session correlation logic.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import PosIngestResponse, PosTransaction

logger = structlog.get_logger("pos")

async def ingest_pos_transactions(
    transactions: list[PosTransaction],
    session: AsyncSession,
) -> PosIngestResponse:
    accepted = 0
    rejected = 0
    errors = []

    if not transactions:
        return PosIngestResponse(accepted=0, rejected=0, errors=[])

    # 1. Batch Insert Transactions
    rows = []
    for tx in transactions:
        rows.append({
            "transaction_id": tx.transaction_id,
            "store_id":       tx.store_id,
            "timestamp":      tx.timestamp,
            "basket_value":   tx.basket_value_inr,
        })

    insert_sql = text("""
        INSERT INTO pos_transactions (transaction_id, store_id, timestamp, basket_value)
        VALUES (:transaction_id, :store_id, :timestamp, :basket_value)
        ON CONFLICT (transaction_id) DO NOTHING
        RETURNING transaction_id
    """)

    try:
        result = await session.execute(insert_sql, rows)
        inserted_ids = [row[0] for row in result.fetchall()]
        accepted += len(inserted_ids)
        # Transactions that already existed are not strictly an error, just idempotent skip
    except Exception as exc:
        logger.error("pos_batch_insert_failed", error=str(exc))
        return PosIngestResponse(
            accepted=0,
            rejected=len(transactions),
            errors=[f"Batch insert failed: {exc}"]
        )

    # 2. Correlate with Sessions
    # For every new transaction, mark sessions as converted if they reached billing
    # and were active (exit_ts is NULL or within 5 mins before tx)
    # in the 5 minutes before the transaction.
    
    correlation_sql = text("""
        WITH matching_sessions AS (
            SELECT s.session_id
            FROM sessions s
            WHERE s.store_id = :store_id
              AND s.reached_billing = true
              AND s.is_converted = false
              AND s.entry_ts <= :tx_timestamp
              AND (s.exit_ts IS NULL OR s.exit_ts >= (:tx_timestamp - INTERVAL '5 minutes'))
        )
        UPDATE sessions
        SET is_converted = true
        WHERE session_id IN (SELECT session_id FROM matching_sessions)
    """)

    correlated_count = 0
    try:
        # Since we only want to correlate newly inserted transactions to avoid duplicate work,
        # we filter the original list.
        inserted_set = set(inserted_ids)
        new_transactions = [tx for tx in transactions if tx.transaction_id in inserted_set]

        for tx in new_transactions:
            corr_result = await session.execute(correlation_sql, {
                "store_id": tx.store_id,
                "tx_timestamp": tx.timestamp
            })
            correlated_count += corr_result.rowcount
            
        await session.commit()
    except Exception as exc:
        logger.error("pos_correlation_failed", error=str(exc))
        await session.rollback()
        return PosIngestResponse(
            accepted=accepted,
            rejected=0,
            errors=[f"Correlation step failed: {exc}"]
        )

    logger.info(
        "pos_ingest_complete",
        accepted=accepted,
        correlated_sessions=correlated_count
    )

    return PosIngestResponse(
        accepted=accepted,
        rejected=0,
        errors=[]
    )
