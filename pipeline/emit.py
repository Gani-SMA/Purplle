import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
import json
import structlog
import numpy as np

# Add parent directory to sys.path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))
try:
    from models import StoreEvent, EventType, EventMetadata
except ImportError:
    # Fallback/mock definitions if models cannot be imported
    from enum import Enum
    class EventType(str, Enum):
        ENTRY = "ENTRY"
        EXIT = "EXIT"
        ZONE_ENTER = "ZONE_ENTER"
        ZONE_EXIT = "ZONE_EXIT"
        ZONE_DWELL = "ZONE_DWELL"
        BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
        BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
        REENTRY = "REENTRY"

logger = structlog.get_logger("emitter")

class VisitorStateMachine:
    def __init__(self, store_id, camera_id, output_path="events.jsonl"):
        self.store_id = store_id
        self.camera_id = camera_id
        self.output_path = output_path
        
        # Track active visitors: visitor_id -> status dict
        self.active_visitors = {}
        
        # Cross-camera seen list to avoid double-counting in overlapping cameras
        # visitor_id -> last_seen_timestamp
        self.cam_seen = {}

    def _write_event(self, event_dict):
        """Appends a validated event dict to the JSONL file."""
        # Simple schema validation
        try:
            # Check if models were imported, if so validate
            if 'StoreEvent' in globals():
                # StoreEvent requires event_id to be a valid UUID
                # If not provided, it auto-generates one.
                ev = StoreEvent(**event_dict)
                event_dict = json.loads(ev.model_dump_json())
            
            with open(self.output_path, "a") as f:
                f.write(json.dumps(event_dict) + "\n")
            logger.info("event_emitted", event_type=event_dict["event_type"], visitor_id=event_dict["visitor_id"])
            return event_dict  # return for Redis update
        except Exception as e:
            logger.error("event_validation_failed", error=str(e), event_data=event_dict)
            return None

    async def _update_cam_status(self, redis, timestamp: datetime):
        """Persist per-camera live status to Redis so the dashboard can read it."""
        try:
            key = f"cam_status:{self.store_id}:{self.camera_id}"
            raw = await redis.get(key)
            count_today = 0
            if raw:
                try:
                    existing = json.loads(raw)
                    count_today = int(existing.get("count_today", 0))
                except Exception:
                    pass
            count_today += 1
            payload = json.dumps({
                "last_seen": timestamp.isoformat(),
                "count_today": count_today,
            })
            # TTL of 25 hours so it auto-expires overnight
            await redis.set(key, payload, ex=90000)
        except Exception as e:
            logger.error("cam_status_update_failed", error=str(e))

    async def handle_detection(self, track_id, visitor_id, is_staff, confidence, zone_id, timestamp, redis, embedding=None):
        """
        Processes a person detection in a frame.
        timestamp: datetime object
        """
        now_ts = timestamp
        
        # Update per-camera live status in Redis on every detection
        await self._update_cam_status(redis, now_ts)

        # Check if visitor is already active
        if visitor_id not in self.active_visitors:
            # ── Cross-camera deduplication ───────────────────────────────────
            cam_seen_key = f"cam_seen:{self.store_id}:{visitor_id}"
            already_seen = await redis.get(cam_seen_key)
            
            # Check exit pool to see if it was a Reentry
            event_type = EventType.ENTRY
            pool_key = f"exit_pool:{self.store_id}"
            had_exited = await redis.hexists(pool_key, visitor_id)
            if had_exited:
                event_type = EventType.REENTRY
                await redis.hdel(pool_key, visitor_id)

            session_seq = 1
            if not already_seen:
                # Emit ENTRY / REENTRY
                event_dict = {
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": visitor_id,
                    "event_type": event_type.value,
                    "timestamp": now_ts.isoformat(),
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": is_staff,
                    "confidence": float(confidence),
                    "metadata": {
                        "queue_depth": None,
                        "sku_zone": None,
                        "session_seq": session_seq
                    }
                }
                self._write_event(event_dict)
                # Mark as seen on this camera for 5 seconds
                await redis.set(cam_seen_key, "1", ex=5)
            else:
                logger.debug("cross_camera_dedup_skip", visitor_id=visitor_id)

            # Initialize active tracking state
            self.active_visitors[visitor_id] = {
                "track_id": track_id,
                "is_staff": is_staff,
                "current_zone": None,
                "zone_enter_time": None,
                "last_dwell_emit": None,
                "reached_billing": False,
                "joined_queue": False,
                "session_seq": session_seq,
                "last_seen": now_ts,
                "confidence": confidence,
                "embedding": embedding
            }

        state = self.active_visitors[visitor_id]
        state["last_seen"] = now_ts
        state["confidence"] = max(state["confidence"], confidence)
        if embedding is not None:
            state["embedding"] = embedding

        # ── Zone transition logic ────────────────────────────────────────────
        prev_zone = state["current_zone"]
        if zone_id != prev_zone:
            # If leaving a zone
            if prev_zone is not None:
                dwell_td = now_ts - state["zone_enter_time"]
                dwell_ms = int(dwell_td.total_seconds() * 1000)
                
                # Emit ZONE_EXIT
                state["session_seq"] += 1
                exit_dict = {
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": visitor_id,
                    "event_type": EventType.ZONE_EXIT.value,
                    "timestamp": now_ts.isoformat(),
                    "zone_id": prev_zone,
                    "dwell_ms": dwell_ms,
                    "is_staff": is_staff,
                    "confidence": float(confidence),
                    "metadata": {
                        "queue_depth": None,
                        "sku_zone": None,
                        "session_seq": state["session_seq"]
                    }
                }
                
                # Special Billing Abandon logic
                if prev_zone == "ZONE_BILLING" and state["joined_queue"] and not state["reached_billing"]:
                    # Emit BILLING_QUEUE_ABANDON
                    state["session_seq"] += 1
                    abandon_dict = {
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": visitor_id,
                        "event_type": EventType.BILLING_QUEUE_ABANDON.value,
                        "timestamp": now_ts.isoformat(),
                        "zone_id": prev_zone,
                        "dwell_ms": 0,
                        "is_staff": is_staff,
                        "confidence": float(confidence),
                        "metadata": {
                            "queue_depth": None,
                            "sku_zone": None,
                            "session_seq": state["session_seq"]
                        }
                    }
                    self._write_event(abandon_dict)
                
                self._write_event(exit_dict)

            # Entering a new zone
            state["current_zone"] = zone_id
            state["zone_enter_time"] = now_ts
            state["last_dwell_emit"] = now_ts
            
            if zone_id is not None:
                state["session_seq"] += 1
                
                # Special Billing queue logic
                event_type = EventType.ZONE_ENTER
                queue_depth = None
                
                if zone_id == "ZONE_BILLING":
                    q_depth_str = await redis.get(f"queue_depth:{self.store_id}")
                    q_depth = int(q_depth_str) if q_depth_str else 0
                    if q_depth > 0:
                        event_type = EventType.BILLING_QUEUE_JOIN
                        queue_depth = q_depth
                        state["joined_queue"] = True
                
                enter_dict = {
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": visitor_id,
                    "event_type": event_type.value,
                    "timestamp": now_ts.isoformat(),
                    "zone_id": zone_id,
                    "dwell_ms": 0,
                    "is_staff": is_staff,
                    "confidence": float(confidence),
                    "metadata": {
                        "queue_depth": queue_depth,
                        "sku_zone": None,
                        "session_seq": state["session_seq"]
                    }
                }
                self._write_event(enter_dict)

        else:
            # Check for ZONE_DWELL (every 30 seconds)
            if zone_id is not None and state["zone_enter_time"] is not None:
                dwell_since_emit = now_ts - state["last_dwell_emit"]
                if dwell_since_emit.total_seconds() >= 30.0:
                    state["session_seq"] += 1
                    total_dwell_td = now_ts - state["zone_enter_time"]
                    total_dwell_ms = int(total_dwell_td.total_seconds() * 1000)
                    
                    dwell_dict = {
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": visitor_id,
                        "event_type": EventType.ZONE_DWELL.value,
                        "timestamp": now_ts.isoformat(),
                        "zone_id": zone_id,
                        "dwell_ms": total_dwell_ms,
                        "is_staff": is_staff,
                        "confidence": float(confidence),
                        "metadata": {
                            "queue_depth": None,
                            "sku_zone": None,
                            "session_seq": state["session_seq"]
                        }
                    }
                    self._write_event(dwell_dict)
                    state["last_dwell_emit"] = now_ts

    async def handle_lost_visitors(self, current_time, redis, max_lost_seconds=5.0):
        """
        Identifies visitors who haven't been detected recently and emits EXIT events.
        """
        lost_visitor_ids = []
        for visitor_id, state in self.active_visitors.items():
            lost_duration = current_time - state["last_seen"]
            if lost_duration.total_seconds() > max_lost_seconds:
                lost_visitor_ids.append(visitor_id)

        for visitor_id in lost_visitor_ids:
            state = self.active_visitors.pop(visitor_id)
            
            # If they were in a zone when they disappeared, emit ZONE_EXIT first
            if state["current_zone"] is not None:
                dwell_td = state["last_seen"] - state["zone_enter_time"]
                dwell_ms = int(dwell_td.total_seconds() * 1000)
                state["session_seq"] += 1
                
                exit_zone_dict = {
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": visitor_id,
                    "event_type": EventType.ZONE_EXIT.value,
                    "timestamp": state["last_seen"].isoformat(),
                    "zone_id": state["current_zone"],
                    "dwell_ms": dwell_ms,
                    "is_staff": state["is_staff"],
                    "confidence": float(state["confidence"]),
                    "metadata": {
                        "queue_depth": None,
                        "sku_zone": None,
                        "session_seq": state["session_seq"]
                    }
                }
                self._write_event(exit_zone_dict)

            # Emit EXIT event
            state["session_seq"] += 1
            exit_dict = {
                "event_id": str(uuid.uuid4()),
                "store_id": self.store_id,
                "camera_id": self.camera_id,
                "visitor_id": visitor_id,
                "event_type": EventType.EXIT.value,
                "timestamp": state["last_seen"].isoformat(),
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": state["is_staff"],
                "confidence": float(state["confidence"]),
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": None,
                    "session_seq": state["session_seq"]
                }
            }
            self._write_event(exit_dict)

            # Add to Re-ID exit pool in Redis (60-minute TTL)
            if state["embedding"] is not None:
                pool_key = f"exit_pool:{self.store_id}"
                info = {
                    "embedding": state["embedding"].tolist() if isinstance(state["embedding"], np.ndarray) else state["embedding"],
                    "exit_time": state["last_seen"].isoformat()
                }
                await redis.hset(pool_key, visitor_id, json.dumps(info))
                await redis.expire(pool_key, 3600)

