import sys
import uuid
from datetime import datetime, timezone
import httpx

BASE_URL = "http://localhost:8000"
HEADERS = {"x-api-key": "test_key_1", "Content-Type": "application/json"}
STORE_ID = "STR001"

def run_assertions():
    print("Starting 10 acceptance assertions...")

    # 1. GET /health -> 200, status field present
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    body = r.json()
    assert "status" in body, "health response missing 'status' field"
    assert "Traceback" not in r.text and "File " not in r.text, "health response contains traceback"
    print("Assertion 1 passed: GET /health")

    # 2. POST /events/ingest with 1 valid event -> accepted=1
    event_id = str(uuid.uuid4())
    event = {
        "event_id": event_id,
        "store_id": STORE_ID,
        "camera_id": "CAM001",
        "visitor_id": f"VIS-{uuid.uuid4().hex[:8].upper()}",
        "event_type": "ENTRY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {"session_seq": 1}
    }
    r = httpx.post(f"{BASE_URL}/events/ingest", json={"events": [event]}, headers=HEADERS)
    assert r.status_code == 200, f"Ingest failed: {r.text}"
    body = r.json()
    assert body.get("accepted") == 1, f"Expected 1 accepted, got {body}"
    assert body.get("rejected") == 0, f"Expected 0 rejected, got {body}"
    assert "Traceback" not in r.text and "File " not in r.text, "ingest response contains traceback"
    print("Assertion 2 passed: POST /events/ingest (1 valid)")

    # 3. Idempotent POST (same event twice) -> accepted=0 on second
    r = httpx.post(f"{BASE_URL}/events/ingest", json={"events": [event]}, headers=HEADERS)
    assert r.status_code == 200, f"Ingest duplicate failed: {r.text}"
    body = r.json()
    assert body.get("accepted") == 0, f"Expected 0 accepted for duplicate, got {body}"
    assert body.get("rejected") == 0, f"Expected 0 rejected for duplicate, got {body}"
    assert "Traceback" not in r.text and "File " not in r.text, "duplicate ingest response contains traceback"
    print("Assertion 3 passed: Idempotency check")

    # 4. Malformed event in batch -> rejected=1, errors[0].reason non-empty
    malformed_event = event.copy()
    malformed_event["event_id"] = str(uuid.uuid4())
    malformed_event["event_type"] = "ZONE_ENTER"
    malformed_event["zone_id"] = None # invalid for ZONE_ENTER
    r = httpx.post(f"{BASE_URL}/events/ingest", json={"events": [malformed_event]}, headers=HEADERS)
    if r.status_code == 200:
        body = r.json()
        assert body.get("rejected") == 1, f"Expected 1 rejected, got {body}"
        assert len(body.get("errors", [])) > 0, "Expected error list"
        assert body["errors"][0].get("reason"), "Expected error reason"
    else:
        assert r.status_code == 422, f"Expected 422 or 200, got {r.status_code}: {r.text}"
    assert "Traceback" not in r.text and "File " not in r.text, "malformed response contains traceback"
    print("Assertion 4 passed: Malformed event validation")

    # 5. GET /stores/STR001/metrics -> 200, all required fields present, no nulls
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/metrics", headers=HEADERS)
    assert r.status_code == 200, f"Metrics failed: {r.text}"
    body = r.json()
    for field in ["store_id", "unique_visitors", "conversion_rate", "avg_dwell_by_zone", "queue_depth", "abandonment_rate"]:
        assert field in body, f"Missing metric field '{field}'"
        assert body[field] is not None, f"Metric field '{field}' is null"
    assert "Traceback" not in r.text and "File " not in r.text, "metrics response contains traceback"
    print("Assertion 5 passed: GET /stores/STR001/metrics")

    # 6. GET /stores/STR001/funnel -> 200, 4 stages, drop_off_pct numeric
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/funnel", headers=HEADERS)
    assert r.status_code == 200, f"Funnel failed: {r.text}"
    body = r.json()
    assert "stages" in body, "funnel missing 'stages'"
    assert len(body["stages"]) == 4, f"Expected 4 stages, got {len(body['stages'])}"
    for stage in body["stages"]:
        assert "stage" in stage
        assert "count" in stage
        assert isinstance(stage["drop_off_pct"], (int, float)), f"drop_off_pct not numeric: {stage['drop_off_pct']}"
    assert "Traceback" not in r.text and "File " not in r.text, "funnel response contains traceback"
    print("Assertion 6 passed: GET /stores/STR001/funnel")

    # 7. GET /stores/STR001/heatmap -> 200, zones list, data_confidence bool
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/heatmap", headers=HEADERS)
    assert r.status_code == 200, f"Heatmap failed: {r.text}"
    body = r.json()
    assert "zones" in body, "heatmap missing 'zones'"
    assert isinstance(body["zones"], list), "zones is not a list"
    assert isinstance(body.get("data_confidence"), bool), "data_confidence is not a bool"
    assert "Traceback" not in r.text and "File " not in r.text, "heatmap response contains traceback"
    print("Assertion 7 passed: GET /stores/STR001/heatmap")

    # 8. GET /stores/STR001/anomalies -> 200, anomalies list
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/anomalies", headers=HEADERS)
    assert r.status_code == 200, f"Anomalies failed: {r.text}"
    body = r.json()
    assert "anomalies" in body, "anomalies response missing 'anomalies' field"
    assert isinstance(body["anomalies"], list), "anomalies is not a list"
    for a in body["anomalies"]:
        assert "severity" in a
        assert a["severity"] in ("INFO", "WARN", "CRITICAL")
        assert "message" in a
        assert "suggested_action" in a
    assert "Traceback" not in r.text and "File " not in r.text, "anomalies response contains traceback"
    print("Assertion 8 passed: GET /stores/STR001/anomalies")

    # 9. GET /stores/DOES_NOT_EXIST/metrics -> 404
    r = httpx.get(f"{BASE_URL}/stores/DOES_NOT_EXIST/metrics", headers=HEADERS)
    assert r.status_code == 404, f"Expected 404 for invalid store, got {r.status_code}"
    assert "Traceback" not in r.text and "File " not in r.text, "404 response contains traceback"
    print("Assertion 9 passed: GET /stores/DOES_NOT_EXIST/metrics -> 404")

    # 10. No endpoint returns a raw Python traceback in response body
    r_unauthorized = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/metrics") # missing key -> 401
    assert "Traceback" not in r_unauthorized.text and "File " not in r_unauthorized.text
    r_bad_method = httpx.post(f"{BASE_URL}/stores/{STORE_ID}/metrics", json={}, headers=HEADERS) # Method not allowed -> 405
    assert "Traceback" not in r_bad_method.text and "File " not in r_bad_method.text
    print("Assertion 10 passed: Traceback prevention validated")

    print("\nALL ASSERTIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        run_assertions()
    except AssertionError as e:
        print(f"\nASSERTION FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
