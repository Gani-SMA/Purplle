# PROMPT: Write a pytest file testing all pipeline components: zones, staff classification, tracker Re-ID matching, state machine, and upload.
# CHANGES MADE: Created test cases validating ZoneClassifier centroid classification, StaffClassifier upper body HSV masks, ReIDTracker reentry cosine matching, and VisitorStateMachine event emission patterns.

import os
import sys
import pytest
import numpy as np
from datetime import datetime, timezone
import json
import uuid
import tempfile

from pipeline.zones import ZoneClassifier
from pipeline.staff import StaffClassifier
from pipeline.tracker import ReIDExtractor, ReIDTracker
from pipeline.emit import VisitorStateMachine, EventType

class MockRedis:
    def __init__(self):
        self.store = {}
        self.ex_store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            self.ex_store[key] = ex

    async def hexists(self, key, field):
        return field in self.store.get(key, {})

    async def hgetall(self, key):
        return self.store.get(key, {})

    async def hset(self, key, field, value):
        if key not in self.store:
            self.store[key] = {}
        self.store[key][field] = value

    async def hdel(self, key, field):
        if key in self.store and field in self.store[key]:
            del self.store[key][field]

    async def expire(self, key, seconds):
        self.ex_store[key] = seconds

@pytest.fixture
def mock_redis():
    return MockRedis()

def test_zone_classifier():
    # Write a temporary store layout json
    layout_data = {
      "STR_TEST": {
        "CAM_TEST": {
          "ZONE_A": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]],
          "ZONE_B": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]]
        }
      }
    }
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(layout_data, f)
        temp_path = f.name
        
    try:
        classifier = ZoneClassifier(layout_path=temp_path)
        
        # Test bbox centroid in Zone A: (0.25, 0.25)
        # norm_bbox is [xmin, ymin, xmax, ymax]
        zone = classifier.classify_zone("STR_TEST", "CAM_TEST", [0.2, 0.2, 0.3, 0.3])
        assert zone == "ZONE_A"
        
        # Test bbox centroid in Zone B: (0.75, 0.25)
        zone = classifier.classify_zone("STR_TEST", "CAM_TEST", [0.7, 0.2, 0.8, 0.3])
        assert zone == "ZONE_B"
        
        # Test bbox centroid outside both: (0.75, 0.75)
        zone = classifier.classify_zone("STR_TEST", "CAM_TEST", [0.7, 0.7, 0.8, 0.8])
        assert zone is None
    finally:
        os.remove(temp_path)

def test_staff_classifier():
    classifier = StaffClassifier()
    # Test fallback mode when frame is None
    assert classifier.is_staff_member(None, [0, 0, 100, 100]) == False

    # Test with blank mock image (should not be classified as staff)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    assert classifier.is_staff_member(img, [10, 10, 90, 90]) == False

    # Test with purple uniform upper body crop
    img_purple = np.zeros((100, 100, 3), dtype=np.uint8)
    img_purple[0:30, 0:100] = [180, 0, 180] # paint upper 30% BGR purple
    
    # Check if staff classifier detects it
    is_staff = classifier.is_staff_member(img_purple, [0, 0, 100, 100], threshold_pct=5.0)
    assert is_staff == True

@pytest.mark.asyncio
async def test_reid_tracker(mock_redis):
    tracker = ReIDTracker(similarity_threshold=0.85)
    store_id = "STR_TEST"
    visitor_id = "VIS_12345"
    
    # 512-dim L2 normalized embeddings
    emb1 = np.ones(512, dtype=np.float32)
    emb1 /= np.linalg.norm(emb1)
    
    # Save exit
    await tracker.add_to_exit_pool(store_id, visitor_id, emb1, datetime.now(timezone.utc).isoformat(), mock_redis)
    
    # Test match with exact same embedding (cos similarity should be 1.0)
    matched_id, sim = await tracker.match_reentry(store_id, emb1, mock_redis)
    assert matched_id == visitor_id
    assert sim >= 0.99

    # Test mismatch with orthogonal embedding
    emb_orth = np.zeros(512, dtype=np.float32)
    emb_orth[0] = 1.0 # different direction
    matched_id, sim = await tracker.match_reentry(store_id, emb_orth, mock_redis)
    assert matched_id is None

@pytest.mark.asyncio
async def test_state_machine_entry_exit(mock_redis):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        temp_path = f.name
        
    try:
        sm = VisitorStateMachine("STR_TEST", "CAM_TEST", temp_path)
        visitor_id = "VIS_XYZ"
        now = datetime.now(timezone.utc)
        
        # 1. First detection (should emit ENTRY)
        await sm.handle_detection(
            track_id=1,
            visitor_id=visitor_id,
            is_staff=False,
            confidence=0.90,
            zone_id=None,
            timestamp=now,
            redis=mock_redis
        )
        
        # Verify events.jsonl has ENTRY event
        with open(temp_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == EventType.ENTRY.value
        assert event["visitor_id"] == visitor_id
        
        # 2. Enter a zone (should emit ZONE_ENTER)
        await sm.handle_detection(
            track_id=1,
            visitor_id=visitor_id,
            is_staff=False,
            confidence=0.90,
            zone_id="ZONE_SKINCARE",
            timestamp=now + timedelta_seconds(5),
            redis=mock_redis
        )
        
        with open(temp_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2
        event = json.loads(lines[1])
        assert event["event_type"] == EventType.ZONE_ENTER.value
        assert event["zone_id"] == "ZONE_SKINCARE"

        # 3. Leave active tracking (should emit ZONE_EXIT and EXIT)
        await sm.handle_lost_visitors(now + timedelta_seconds(20), mock_redis, max_lost_seconds=10.0)
        
        with open(temp_path, "r") as f:
            lines = f.readlines()
        # Should have appended ZONE_EXIT and EXIT
        assert len(lines) == 4
        assert json.loads(lines[2])["event_type"] == EventType.ZONE_EXIT.value
        assert json.loads(lines[3])["event_type"] == EventType.EXIT.value
        
    finally:
        os.remove(temp_path)

def timedelta_seconds(seconds):
    return timedelta_seconds_helper(seconds)

def timedelta_seconds_helper(seconds):
    from datetime import timedelta
    return timedelta(seconds=seconds)
