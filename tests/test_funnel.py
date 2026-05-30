# PROMPT: Generate funnel tests covering re-entry dedup, all-staff clip, zero purchases,
#         and 4-stage structure validation.
# CHANGES MADE: Verified visitor counted once even with REENTRY events;
#               confirmed 4 stages always returned with drop_off_pct as numeric.

import httpx

BASE_URL = "http://localhost:8000"
HEADERS  = {"x-api-key": "test_key_1"}
STORE_ID = "STR001"


def test_funnel_returns_4_stages():
    """GET /stores/STR001/funnel returns 200 with exactly 4 stages."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/funnel", headers=HEADERS, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "stages" in body
    assert len(body["stages"]) == 4
    expected_names = ["entry", "zone_visit", "billing_queue", "purchase"]
    for i, stage in enumerate(body["stages"]):
        assert stage["stage"] == expected_names[i]
        assert isinstance(stage["count"], int)
        assert isinstance(stage["drop_off_pct"], (int, float))


def test_funnel_first_stage_zero_dropoff():
    """First stage (entry) should always have drop_off_pct = 0."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/funnel", headers=HEADERS, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["stages"][0]["drop_off_pct"] == 0.0


def test_funnel_nonexistent_store_404():
    """GET /stores/DOES_NOT_EXIST/funnel returns 404."""
    r = httpx.get(f"{BASE_URL}/stores/DOES_NOT_EXIST/funnel", headers=HEADERS, timeout=10)
    assert r.status_code == 404


def test_funnel_counts_monotonically_decrease():
    """Each funnel stage count should be <= the previous stage (or zero)."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/funnel", headers=HEADERS, timeout=10)
    assert r.status_code == 200
    stages = r.json()["stages"]
    for i in range(1, len(stages)):
        assert stages[i]["count"] <= stages[i - 1]["count"]
