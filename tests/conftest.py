"""
tests/conftest.py — Shared async fixtures for all test modules.
Uses httpx AsyncClient against the real running API (localhost:8000).
"""
import pytest
import httpx

BASE_URL  = "http://localhost:8000"
API_KEY   = "test_key_1"
HEADERS   = {"x-api-key": API_KEY, "Content-Type": "application/json"}
STORE_ID  = "STR001"

@pytest.fixture
def base_url():
    return BASE_URL

@pytest.fixture
def headers():
    return HEADERS

@pytest.fixture
def store_id():
    return STORE_ID

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10)
