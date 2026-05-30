"""
Seed script — Phase 2
Inserts realistic sample data for 3 Purplle stores:
  - stores            : 3 rows
  - sessions          : ~50 rows (past 30 days)
  - pos_transactions  : ~30 days × 3 stores × variable volume
  - anomalies_log     : handful of representative rows

Run inside the api container:
  python seed.py
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:pass@db:5432/storedb",
).replace("postgresql+asyncpg://", "postgresql://")

# ─── Reference data ──────────────────────────────────────────────────────────

STORES = [
    {
        "store_id": "STR001",
        "name": "Purplle Mumbai – Andheri",
        "city": "Mumbai",
        "layout": {
            "zones": [
                {"id": "ZONE_ENTRY",    "label": "Entry",         "area_sqft": 120},
                {"id": "ZONE_SKINCARE", "label": "Skincare",      "area_sqft": 350},
                {"id": "ZONE_MAKEUP",   "label": "Makeup",        "area_sqft": 300},
                {"id": "ZONE_HAIRCARE", "label": "Haircare",      "area_sqft": 200},
                {"id": "ZONE_BILLING",  "label": "Billing",       "area_sqft": 80},
            ],
            "total_sqft": 1050,
        },
        "open_hours": {"Mon-Sat": "10:00-21:00", "Sun": "11:00-20:00"},
        "cameras": [
            {"camera_id": "CAM001", "zone_id": "ZONE_ENTRY",    "model": "Hikvision-4K"},
            {"camera_id": "CAM002", "zone_id": "ZONE_SKINCARE", "model": "Hikvision-4K"},
            {"camera_id": "CAM003", "zone_id": "ZONE_MAKEUP",   "model": "Dahua-2K"},
            {"camera_id": "CAM004", "zone_id": "ZONE_BILLING",  "model": "Dahua-2K"},
        ],
    },
    {
        "store_id": "STR002",
        "name": "Purplle Delhi – Connaught Place",
        "city": "Delhi",
        "layout": {
            "zones": [
                {"id": "ZONE_ENTRY",      "label": "Entry",         "area_sqft": 100},
                {"id": "ZONE_SKINCARE",   "label": "Skincare",      "area_sqft": 400},
                {"id": "ZONE_MAKEUP",     "label": "Makeup",        "area_sqft": 350},
                {"id": "ZONE_FRAGRANCE",  "label": "Fragrance",     "area_sqft": 150},
                {"id": "ZONE_BILLING",    "label": "Billing",       "area_sqft": 90},
            ],
            "total_sqft": 1090,
        },
        "open_hours": {"Mon-Sat": "10:00-21:00", "Sun": "11:00-20:00"},
        "cameras": [
            {"camera_id": "CAM005", "zone_id": "ZONE_ENTRY",     "model": "Hikvision-4K"},
            {"camera_id": "CAM006", "zone_id": "ZONE_SKINCARE",  "model": "Hikvision-4K"},
            {"camera_id": "CAM007", "zone_id": "ZONE_MAKEUP",    "model": "Dahua-2K"},
            {"camera_id": "CAM008", "zone_id": "ZONE_BILLING",   "model": "Dahua-2K"},
        ],
    },
    {
        "store_id": "STR003",
        "name": "Purplle Bengaluru – Koramangala",
        "city": "Bengaluru",
        "layout": {
            "zones": [
                {"id": "ZONE_ENTRY",    "label": "Entry",         "area_sqft": 90},
                {"id": "ZONE_SKINCARE", "label": "Skincare",      "area_sqft": 320},
                {"id": "ZONE_MAKEUP",   "label": "Makeup",        "area_sqft": 280},
                {"id": "ZONE_WELLNESS", "label": "Wellness",      "area_sqft": 180},
                {"id": "ZONE_BILLING",  "label": "Billing",       "area_sqft": 70},
            ],
            "total_sqft": 940,
        },
        "open_hours": {"Mon-Sat": "10:00-21:30", "Sun": "11:00-20:30"},
        "cameras": [
            {"camera_id": "CAM009", "zone_id": "ZONE_ENTRY",    "model": "Axis-4K"},
            {"camera_id": "CAM010", "zone_id": "ZONE_SKINCARE", "model": "Axis-4K"},
            {"camera_id": "CAM011", "zone_id": "ZONE_MAKEUP",   "model": "Dahua-2K"},
            {"camera_id": "CAM012", "zone_id": "ZONE_BILLING",  "model": "Dahua-2K"},
        ],
    },
]

ANOMALY_TEMPLATES = [
    ("STALE_FEED",    "WARN",     "Camera feed for {store_id} CAM001 has not sent events in 15 minutes.",           "Check camera power and network connectivity."),
    ("QUEUE_SPIKE",   "CRITICAL", "Billing queue depth reached 8 at {store_id} — exceeds threshold of 5.",          "Open an additional billing counter immediately."),
    ("DEAD_ZONE",     "WARN",     "Zone ZONE_WELLNESS in {store_id} had zero visitors for 35 minutes.",             "Review zone product placement and lighting."),
    ("REENTRY",       "INFO",     "Visitor re-entry detected at {store_id} within the 60-minute dedup window.",     "Monitor for potential return/exchange patterns."),
    ("CONVERSION_DROP","WARN",    "Conversion rate at {store_id} dropped 25% vs 7-day average in the last hour.",   "Review ongoing promotions and staff engagement."),
]

NOW = datetime.now(timezone.utc)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def rand_ts(days_back_max: int = 30) -> datetime:
    delta = timedelta(
        days=random.randint(0, days_back_max),
        hours=random.randint(10, 20),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return NOW - delta

def rand_basket() -> float:
    return round(random.uniform(199.0, 3499.0), 2)

# ─── Seeders ─────────────────────────────────────────────────────────────────

async def seed_stores(conn: asyncpg.Connection) -> None:
    print("  → Seeding stores …")
    for s in STORES:
        await conn.execute(
            """
            INSERT INTO stores (store_id, name, city, layout, open_hours, cameras)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb)
            ON CONFLICT (store_id) DO NOTHING
            """,
            s["store_id"],
            s["name"],
            s["city"],
            str(s["layout"]).replace("'", '"'),
            str(s["open_hours"]).replace("'", '"'),
            str(s["cameras"]).replace("'", '"'),
        )
    print(f"     ✓ {len(STORES)} stores ready.")


async def seed_pos(conn: asyncpg.Connection) -> None:
    print("  → Seeding POS transactions …")
    rows: list[tuple] = []
    for store in STORES:
        for day in range(30):
            # 5–25 transactions per store per day
            count = random.randint(5, 25)
            for _ in range(count):
                ts = NOW - timedelta(days=day, hours=random.randint(0, 10), minutes=random.randint(0, 59))
                rows.append((
                    f"TXN-{uuid.uuid4().hex[:12].upper()}",
                    store["store_id"],
                    ts,
                    rand_basket(),
                ))
    await conn.executemany(
        """
        INSERT INTO pos_transactions (transaction_id, store_id, timestamp, basket_value)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (transaction_id) DO NOTHING
        """,
        rows,
    )
    print(f"     ✓ {len(rows)} POS transactions inserted.")


async def seed_sessions(conn: asyncpg.Connection) -> None:
    print("  → Seeding visitor sessions …")
    rows: list[tuple] = []
    zone_sets = [
        ["ZONE_ENTRY", "ZONE_SKINCARE", "ZONE_BILLING"],
        ["ZONE_ENTRY", "ZONE_MAKEUP"],
        ["ZONE_ENTRY", "ZONE_SKINCARE", "ZONE_MAKEUP", "ZONE_BILLING"],
        ["ZONE_ENTRY", "ZONE_HAIRCARE"],
        ["ZONE_ENTRY", "ZONE_WELLNESS", "ZONE_BILLING"],
    ]
    for store in STORES:
        for _ in range(50):
            entry = rand_ts(30)
            dwell_ms = random.randint(3 * 60_000, 45 * 60_000)
            exit_ts = entry + timedelta(milliseconds=dwell_ms)
            converted = random.random() < 0.35
            reached_billing = converted or random.random() < 0.15
            zones = random.choice(zone_sets)
            rows.append((
                str(uuid.uuid4()),
                store["store_id"],
                f"VIS-{uuid.uuid4().hex[:8].upper()}",
                entry,
                exit_ts,
                converted,
                False,           # is_reentry
                dwell_ms,
                zones,
                reached_billing,
                False,           # abandoned_queue
            ))
    await conn.executemany(
        """
        INSERT INTO sessions
          (session_id, store_id, visitor_id, entry_ts, exit_ts,
           is_converted, is_reentry, total_dwell_ms,
           zones_visited, reached_billing, abandoned_queue)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (session_id) DO NOTHING
        """,
        rows,
    )
    print(f"     ✓ {len(rows)} visitor sessions inserted.")


async def seed_anomalies(conn: asyncpg.Connection) -> None:
    print("  → Seeding anomaly log …")
    rows: list[tuple] = []
    for store in STORES:
        for anomaly_type, severity, msg_tpl, action in ANOMALY_TEMPLATES:
            rows.append((
                str(uuid.uuid4()),
                store["store_id"],
                anomaly_type,
                severity,
                msg_tpl.format(store_id=store["store_id"]),
                action,
                rand_ts(7),
                None,
            ))
    await conn.executemany(
        """
        INSERT INTO anomalies_log
          (id, store_id, anomaly_type, severity, message, suggested_action, detected_at, resolved_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )
    print(f"     ✓ {len(rows)} anomaly entries inserted.")


async def main() -> None:
    print("\n🌱 Purplle Store Intelligence — Seed Script (Phase 2)\n")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await seed_stores(conn)
        await seed_pos(conn)
        await seed_sessions(conn)
        await seed_anomalies(conn)
    finally:
        await conn.close()
    print("\n✅ Seed complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
