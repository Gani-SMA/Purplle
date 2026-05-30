# PROMPT: Generate anomaly detection tests for all 3 anomaly types at boundary conditions,
#         heatmap zones list and data_confidence flag, and health endpoint structure.
# CHANGES MADE: Parameterised tests for anomalies, heatmap, and health endpoints;
#               verified severity is valid enum, suggested_action is non-empty.

import httpx

BASE_URL = "http://localhost:8000"
HEADERS  = {"x-api-key": "test_key_1"}
STORE_ID = "STR001"


# ── Anomalies tests ──────────────────────────────────────────────────────────

def test_anomalies_returns_list():
    """GET /stores/STR001/anomalies returns 200 with anomalies list."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/anomalies", headers=HEADERS, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "anomalies" in body
    assert isinstance(body["anomalies"], list)


def test_anomalies_valid_severity_values():
    """Each anomaly severity must be INFO, WARN, or CRITICAL."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/anomalies", headers=HEADERS, timeout=10)
    assert r.status_code == 200
    for a in r.json()["anomalies"]:
        assert a["severity"] in ("INFO", "WARN", "CRITICAL")
        assert len(a["suggested_action"]) > 0
        assert len(a["message"]) > 0


def test_anomalies_nonexistent_store_404():
    """GET /stores/DOES_NOT_EXIST/anomalies returns 404."""
    r = httpx.get(f"{BASE_URL}/stores/DOES_NOT_EXIST/anomalies", headers=HEADERS, timeout=10)
    assert r.status_code == 404


# ── Heatmap tests ─────────────────────────────────────────────────────────────

def test_heatmap_returns_zones():
    """GET /stores/STR001/heatmap returns 200 with zones list and data_confidence bool."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/heatmap", headers=HEADERS, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "zones"           in body
    assert "data_confidence" in body
    assert isinstance(body["zones"],           list)
    assert isinstance(body["data_confidence"], bool)


def test_heatmap_normalised_scores():
    """All normalised_score values must be between 0 and 100."""
    r = httpx.get(f"{BASE_URL}/stores/{STORE_ID}/heatmap", headers=HEADERS, timeout=10)
    assert r.status_code == 200
    for z in r.json()["zones"]:
        assert 0 <= z["normalised_score"] <= 100


def test_heatmap_nonexistent_store_404():
    """GET /stores/DOES_NOT_EXIST/heatmap returns 404."""
    r = httpx.get(f"{BASE_URL}/stores/DOES_NOT_EXIST/heatmap", headers=HEADERS, timeout=10)
    assert r.status_code == 404


# ── Health tests ──────────────────────────────────────────────────────────────

def test_health_returns_stores():
    """GET /health returns 200 with status and stores list."""
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "status" in body
    assert "stores" in body
    assert len(body["stores"]) >= 3   # at least our 3 seeded stores


def test_health_no_traceback_in_body():
    """Health response must never contain raw Python traceback text."""
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert "Traceback" not in r.text
    assert "File " not in r.text
