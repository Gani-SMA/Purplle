import asyncio
import os
import random
import uuid
import json
from datetime import datetime, timedelta, timezone
import asyncpg
import redis.asyncio as aioredis

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:pass@db:5432/storedb",
).replace("postgresql+asyncpg://", "postgresql://")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

STORES_CONFIG = {
    "STR001": {
        "zones": ["ZONE_ENTRY", "ZONE_SKINCARE", "ZONE_MAKEUP", "ZONE_HAIRCARE", "ZONE_BILLING"],
        "cameras": {
            "ZONE_ENTRY": "CAM001",
            "ZONE_SKINCARE": "CAM002",
            "ZONE_MAKEUP": "CAM003",
            "ZONE_HAIRCARE": "CAM002",
            "ZONE_BILLING": "CAM004"
        }
    },
    "STR002": {
        "zones": ["ZONE_ENTRY", "ZONE_SKINCARE", "ZONE_MAKEUP", "ZONE_FRAGRANCE", "ZONE_BILLING"],
        "cameras": {
            "ZONE_ENTRY": "CAM005",
            "ZONE_SKINCARE": "CAM006",
            "ZONE_MAKEUP": "CAM007",
            "ZONE_FRAGRANCE": "CAM006",
            "ZONE_BILLING": "CAM008"
        }
    },
    "STR003": {
        "zones": ["ZONE_ENTRY", "ZONE_SKINCARE", "ZONE_MAKEUP", "ZONE_WELLNESS", "ZONE_BILLING"],
        "cameras": {
            "ZONE_ENTRY": "CAM009",
            "ZONE_SKINCARE": "CAM010",
            "ZONE_MAKEUP": "CAM011",
            "ZONE_WELLNESS": "CAM010",
            "ZONE_BILLING": "CAM012"
        }
    }
}

ANOMALY_TEMPLATES = [
    ("STALE_FEED", "WARN", "Camera feed for {store_id} CAM001 has not sent events in 15 minutes.", "Check camera power and network connectivity."),
    ("QUEUE_SPIKE", "CRITICAL", "Billing queue depth reached 8 at {store_id} — exceeds threshold of 5.", "Open an additional billing counter immediately."),
    ("DEAD_ZONE", "WARN", "Zone ZONE_WELLNESS/FRAGRANCE in {store_id} had zero visitors for 35 minutes.", "Review zone product placement and lighting."),
    ("REENTRY", "INFO", "Visitor re-entry detected at {store_id} within the 60-minute dedup window.", "Monitor for potential return/exchange patterns."),
]

def rand_basket() -> float:
    return round(random.uniform(199.0, 3499.0), 2)

async def seed_today():
    print("Connecting to Database and Redis...")
    conn = await asyncpg.connect(DATABASE_URL)
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    # Check if events already exist to prevent wiping out ingested data on container restart
    event_count = await conn.fetchval("SELECT COUNT(*) FROM events")
    if event_count > 0:
        print("     ℹ Events already exist. Skipping live feed seed, but refreshing Redis live statuses.")
        # Set Redis keys anyway to make sure dashboard shows live status
        now_utc = datetime.now(timezone.utc)
        for store_id in STORES_CONFIG.keys():
            await redis_client.set(f"stale_feed:{store_id}", now_utc.isoformat())
            await redis_client.set(f"queue_depth:{store_id}", str(random.randint(1, 4)))
        await conn.close()
        await redis_client.aclose()
        return

    print("Truncating tables for fresh seed...")
    await conn.execute("TRUNCATE events, sessions, pos_transactions, anomalies_log CASCADE;")

    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=6, minute=0, second=0, microsecond=0) # start today at 6 AM UTC
    
    # We want to distribute visits between today_start and now_utc
    max_duration_seconds = int((now_utc - today_start).total_seconds())
    if max_duration_seconds <= 0:
        max_duration_seconds = 3600 * 4
        today_start = now_utc - timedelta(seconds=max_duration_seconds)

    events_to_insert = []
    sessions_to_insert = []
    txns_to_insert = []
    anomalies_to_insert = []

    for store_id, config in STORES_CONFIG.items():
        print(f"Generating data for {store_id}...")
        
        # 1. Update stale feed status in Redis to mark feed as LIVE
        await redis_client.set(f"stale_feed:{store_id}", now_utc.isoformat())
        await redis_client.set(f"queue_depth:{store_id}", str(random.randint(1, 4)))

        # Generate 45 visitors per store
        for i in range(1, 46):
            visitor_id = f"VIS_{store_id}_{i:03d}"
            
            # Start time randomly distributed throughout the day
            visitor_start = today_start + timedelta(seconds=random.randint(0, max_duration_seconds - 1800))
            
            # Generate the journey steps
            journey = []
            
            # Step 1: Entry
            t_entry = visitor_start
            dwell_entry = random.randint(10, 40)
            t_entry_end = t_entry + timedelta(seconds=dwell_entry)
            journey.append(("ZONE_ENTRY", t_entry, t_entry_end))
            
            # Step 2: Browse 1
            browse_zones = [z for z in config["zones"] if z not in ("ZONE_ENTRY", "ZONE_BILLING")]
            b1 = random.choice(browse_zones)
            t_b1 = t_entry_end
            dwell_b1 = random.randint(60, 400)
            t_b1_end = t_b1 + timedelta(seconds=dwell_b1)
            journey.append((b1, t_b1, t_b1_end))
            
            last_end = t_b1_end
            
            # Step 3: Browse 2 (70% probability)
            if random.random() < 0.70:
                b2 = random.choice([z for z in browse_zones if z != b1])
                t_b2 = last_end
                dwell_b2 = random.randint(60, 400)
                t_b2_end = t_b2 + timedelta(seconds=dwell_b2)
                journey.append((b2, t_b2, t_b2_end))
                last_end = t_b2_end
                
            # Step 4: Billing (45% probability)
            reached_billing = random.random() < 0.45
            is_converted = False
            abandoned_queue = False
            if reached_billing:
                t_bill = last_end
                dwell_bill = random.randint(40, 200)
                t_bill_end = t_bill + timedelta(seconds=dwell_bill)
                journey.append(("ZONE_BILLING", t_bill, t_bill_end))
                last_end = t_bill_end
                
                is_converted = random.random() < 0.80
                if not is_converted:
                    abandoned_queue = random.random() < 0.30

            t_exit = last_end
            
            # Insert events for this journey
            session_seq = 1
            zones_visited = []
            
            for zone_id, start_t, end_t in journey:
                camera_id = config["cameras"].get(zone_id, "CAM001")
                zones_visited.append(zone_id)
                
                # Check if it's entry
                if zone_id == "ZONE_ENTRY":
                    events_to_insert.append((
                        uuid.uuid4(), store_id, camera_id, visitor_id, "ENTRY", start_t,
                        None, 0, False, 0.95, None, None, session_seq, None
                    ))
                    session_seq += 1

                events_to_insert.append((
                    uuid.uuid4(), store_id, camera_id, visitor_id, "ZONE_ENTER", start_t,
                    zone_id, 0, False, 0.95, None, None, session_seq, None
                ))
                session_seq += 1
                
                events_to_insert.append((
                    uuid.uuid4(), store_id, camera_id, visitor_id, "ZONE_EXIT", end_t,
                    zone_id, int((end_t - start_t).total_seconds() * 1000), False, 0.95, None, None, session_seq, None
                ))
                session_seq += 1

            # Exit event
            exit_camera = config["cameras"].get("ZONE_BILLING" if reached_billing else "ZONE_ENTRY", "CAM001")
            events_to_insert.append((
                uuid.uuid4(), store_id, exit_camera, visitor_id, "EXIT", t_exit,
                None, 0, False, 0.95, None, None, session_seq, None
            ))
            
            # Create session
            total_dwell_ms = int((t_exit - t_entry).total_seconds() * 1000)
            sessions_to_insert.append((
                uuid.uuid4(), store_id, visitor_id, t_entry, t_exit,
                is_converted, False, total_dwell_ms, zones_visited,
                reached_billing, abandoned_queue
            ))
            
            # Create POS transaction if converted
            if is_converted:
                txns_to_insert.append((
                    f"TXN-{uuid.uuid4().hex[:12].upper()}", store_id, t_exit, rand_basket()
                ))

        # Generate anomalies for today
        anomaly_count = random.randint(1, len(ANOMALY_TEMPLATES))
        selected_anomalies = random.sample(ANOMALY_TEMPLATES, anomaly_count)
        for anomaly_type, severity, msg_tpl, action in selected_anomalies:
            det_t = today_start + timedelta(seconds=random.randint(0, max_duration_seconds))
            anomalies_to_insert.append((
                uuid.uuid4(), store_id, anomaly_type, severity,
                msg_tpl.format(store_id=store_id), action, det_t, None
            ))

    print(f"Writing {len(events_to_insert)} events to DB...")
    await conn.executemany(
        """
        INSERT INTO events
          (event_id, store_id, camera_id, visitor_id, event_type, timestamp,
           zone_id, dwell_ms, is_staff, confidence, queue_depth, sku_zone, session_seq, raw_metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
        events_to_insert
    )

    print(f"Writing {len(sessions_to_insert)} sessions to DB...")
    await conn.executemany(
        """
        INSERT INTO sessions
          (session_id, store_id, visitor_id, entry_ts, exit_ts,
           is_converted, is_reentry, total_dwell_ms, zones_visited, reached_billing, abandoned_queue)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        sessions_to_insert
    )

    print(f"Writing {len(txns_to_insert)} POS transactions to DB...")
    await conn.executemany(
        """
        INSERT INTO pos_transactions
          (transaction_id, store_id, timestamp, basket_value)
        VALUES ($1, $2, $3, $4)
        """,
        txns_to_insert
    )

    print(f"Writing {len(anomalies_to_insert)} anomalies to DB...")
    await conn.executemany(
        """
        INSERT INTO anomalies_log
          (id, store_id, anomaly_type, severity, message, suggested_action, detected_at, resolved_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        anomalies_to_insert
    )

    await conn.close()
    await redis_client.aclose()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_today())
