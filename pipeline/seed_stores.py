"""
pipeline/seed_stores.py
Generates realistic synthetic visitor-event data for STR002 and STR003
and uploads it directly to the live /events/ingest endpoint.

Usage (from project root, with venv active):
    python pipeline/seed_stores.py
"""

import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "test_key_1")

ZONES = [
    "ZONE_ENTRY",
    "ZONE_SKINCARE",
    "ZONE_MAKEUP",
    "ZONE_HAIRCARE",
    "ZONE_FRAGRANCE",
    "ZONE_BILLING",
]

STORE_CONFIGS = {
    "STR001": {
        "camera_id": "CAM_STR001_01",
        "num_visitors": 428,
        "billing_conversion": 0.45,
        "queue_spike_prob": 0.18,
        "avg_zones_per_visitor": 2.8,
    },
    "STR002": {
        "camera_id": "CAM_STR002_01",
        "num_visitors": 312,
        "billing_conversion": 0.38,   # 38 % reach billing
        "queue_spike_prob": 0.15,
        "avg_zones_per_visitor": 2.4,
    },
    "STR003": {
        "camera_id": "CAM_STR003_01",
        "num_visitors": 487,
        "billing_conversion": 0.52,
        "queue_spike_prob": 0.10,
        "avg_zones_per_visitor": 3.1,
    },
}

BATCH_SIZE = 400


def rand_ts(base: datetime, offset_min: float, jitter_s: float = 30) -> datetime:
    return base + timedelta(seconds=offset_min * 60 + random.uniform(0, jitter_s))


def make_event(
    store_id: str,
    camera_id: str,
    visitor_id: str,
    event_type: str,
    ts: datetime,
    zone_id: str | None = None,
    dwell_ms: int = 0,
    is_staff: bool = False,
    queue_depth: int | None = None,
) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": ts.isoformat(),
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": round(random.uniform(0.72, 0.99), 3),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": None,
            "session_seq": 1,
        },
    }


def generate_events_for_store(store_id: str, cfg: dict) -> list[dict]:
    events: list[dict] = []
    camera_id = cfg["camera_id"]
    num_visitors = cfg["num_visitors"]
    billing_conv = cfg["billing_conversion"]
    queue_spike_prob = cfg["queue_spike_prob"]
    avg_zones = cfg["avg_zones_per_visitor"]

    # Spread visitors across a 9-hour trading day
    day_start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)

    for _ in range(num_visitors):
        visitor_id = f"V_{store_id}_{uuid.uuid4().hex[:10]}"
        is_staff = random.random() < 0.07  # 7 % staff

        # Entry time — uniform across trading hours
        entry_offset_min = random.uniform(0, 9 * 60)
        entry_ts = rand_ts(day_start, entry_offset_min)

        events.append(make_event(
            store_id, camera_id, visitor_id,
            "ENTRY", entry_ts, is_staff=is_staff,
        ))

        # Zone visits
        num_zones = max(1, int(random.gauss(avg_zones, 1.0)))
        visited_zones = random.sample(ZONES[1:], min(num_zones, len(ZONES) - 1))

        current_ts = entry_ts
        for zone_id in visited_zones:
            zone_enter_ts = current_ts + timedelta(seconds=random.uniform(30, 180))
            dwell_s = random.expovariate(1 / 90)  # mean ~90 s
            dwell_s = max(10, min(dwell_s, 900))
            zone_exit_ts = zone_enter_ts + timedelta(seconds=dwell_s)

            events.append(make_event(
                store_id, camera_id, visitor_id,
                "ZONE_ENTER", zone_enter_ts, zone_id=zone_id, is_staff=is_staff,
            ))

            # Billing queue join?
            if zone_id == "ZONE_BILLING":
                q_depth = random.randint(2, 8) if random.random() < queue_spike_prob else 0
                events.append(make_event(
                    store_id, camera_id, visitor_id,
                    "BILLING_QUEUE_JOIN" if q_depth > 0 else "ZONE_ENTER",
                    zone_enter_ts + timedelta(seconds=5),
                    zone_id=zone_id, is_staff=is_staff,
                    queue_depth=q_depth if q_depth > 0 else None,
                ))

            events.append(make_event(
                store_id, camera_id, visitor_id,
                "ZONE_EXIT", zone_exit_ts,
                zone_id=zone_id, dwell_ms=int(dwell_s * 1000), is_staff=is_staff,
            ))
            current_ts = zone_exit_ts

        # Should this visitor reach billing (conversion)?
        if random.random() < billing_conv and "ZONE_BILLING" not in visited_zones:
            bill_ts = current_ts + timedelta(seconds=random.uniform(30, 120))
            dwell_s = random.uniform(60, 300)
            events.append(make_event(
                store_id, camera_id, visitor_id,
                "ZONE_ENTER", bill_ts, zone_id="ZONE_BILLING", is_staff=is_staff,
            ))
            events.append(make_event(
                store_id, camera_id, visitor_id,
                "ZONE_EXIT", bill_ts + timedelta(seconds=dwell_s),
                zone_id="ZONE_BILLING", dwell_ms=int(dwell_s * 1000), is_staff=is_staff,
            ))
            current_ts = bill_ts + timedelta(seconds=dwell_s)

        # Exit
        exit_ts = current_ts + timedelta(seconds=random.uniform(10, 60))
        events.append(make_event(
            store_id, camera_id, visitor_id,
            "EXIT", exit_ts, is_staff=is_staff,
        ))

    return events


async def upload(events: list[dict], store_id: str):
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    batches = [events[i : i + BATCH_SIZE] for i in range(0, len(events), BATCH_SIZE)]
    total_accepted = 0
    total_rejected = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, batch in enumerate(batches):
            resp = await client.post(
                f"{API_URL}/events/ingest",
                json={"events": batch},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                total_accepted += data.get("accepted", 0)
                total_rejected += data.get("rejected", 0)
                print(
                    f"  [{store_id}] batch {i+1}/{len(batches)} — "
                    f"accepted={data.get('accepted')} rejected={data.get('rejected')}"
                )
            else:
                print(f"  [{store_id}] batch {i+1} ERROR {resp.status_code}: {resp.text[:200]}")

    print(f"\n[DONE] {store_id} done - {total_accepted} accepted, {total_rejected} rejected\n")


async def main():
    for store_id, cfg in STORE_CONFIGS.items():
        print(f"\n[SEED] Generating events for {store_id}...")
        events = generate_events_for_store(store_id, cfg)
        print(f"  {len(events)} events generated")
        await upload(events, store_id)


if __name__ == "__main__":
    asyncio.run(main())
