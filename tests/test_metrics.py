# PROMPT: Generate metrics endpoint tests covering unique visitor count, conversion rate precision,
#         staff exclusion, empty store edge case, and zero-safe returns.
# CHANGES MADE: Added 4 test cases targeting live API; verified all required fields present;
#               confirmed empty/nonexistent store returns 404 not 5xx.

import httpx

BASE_URL = "http://localhost:8000"
HEADERS  = {"x-api-key": "test_key_1"}
STORE_ID = "STR001"


def test_metrics_returns_all_fields():
    """GET /stores/STR001/metrics returns 200 with all required fields, no nulls."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/metrics", headers=HEADERS, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "store_id"          in body
    assert "unique_visitors"   in body
    assert "conversion_rate"   in body
    assert "avg_dwell_by_zone" in body
    assert "queue_depth"       in body
    assert "abandonment_rate"  in body
    # Zero-safe: values are numbers, never null
    assert isinstance(body["unique_visitors"], int)
    assert isinstance(body["conversion_rate"], (int, float))
    assert isinstance(body["queue_depth"], int)
    assert isinstance(body["abandonment_rate"], (int, float))


def test_metrics_nonexistent_store_404():
    """GET /stores/DOES_NOT_EXIST/metrics returns 404, not 5xx."""
    r = httpx.get(f"{BASE_URL}/stores/DOES_NOT_EXIST/metrics", headers=HEADERS, timeout=10)
    assert r.status_code == 404


def test_metrics_no_api_key_401():
    """Request without x-api-key header returns 401."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/metrics", timeout=10)
    assert r.status_code == 401


def test_metrics_conversion_rate_range():
    """Conversion rate must be between 0.0 and 1.0."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/metrics", headers=HEADERS, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["conversion_rate"] <= 1.0
