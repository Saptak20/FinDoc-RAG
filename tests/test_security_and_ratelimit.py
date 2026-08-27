import asyncio
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import Settings, settings
from app.core.rate_limiter import limiter, parse_rate_limit
from app.main import app


def test_parse_rate_limit():
    """Verify rate limit string parsing for various intervals."""
    count, sec = parse_rate_limit("30/minute")
    assert count == 30
    assert sec == 60

    count, sec = parse_rate_limit("10/second")
    assert count == 10
    assert sec == 1

    count, sec = parse_rate_limit("100/hour")
    assert count == 100
    assert sec == 3600

    count, sec = parse_rate_limit("500/day")
    assert count == 500
    assert sec == 86400

    # Default fallback
    count, sec = parse_rate_limit("invalid_format")
    assert count == 60
    assert sec == 60


def test_in_memory_rate_limiter_mechanism():
    """Verify in-memory sliding window limiter blocks requests exceeding quota."""
    limiter.reset()

    # Allow 2 requests per 10 seconds
    client_id = "192.168.1.50"
    endpoint = "test_ep"

    limited, _ = limiter.is_rate_limited(client_id, endpoint, max_requests=2, window_seconds=10)
    assert limited is False

    limited, _ = limiter.is_rate_limited(client_id, endpoint, max_requests=2, window_seconds=10)
    assert limited is False

    # 3rd request should be blocked
    limited, retry_after = limiter.is_rate_limited(client_id, endpoint, max_requests=2, window_seconds=10)
    assert limited is True
    assert retry_after >= 1

    # Different client should not be blocked
    other_client_limited, _ = limiter.is_rate_limited("192.168.1.51", endpoint, max_requests=2, window_seconds=10)
    assert other_client_limited is False

    limiter.reset()


def test_rate_limiting_http_429_response():
    """Verify rate limited endpoint returns HTTP 429 and Retry-After header."""
    client = TestClient(app)
    limiter.reset()

    original_rate = settings.RATE_LIMIT_CHAT
    try:
        # Temporarily set very restrictive rate
        settings.RATE_LIMIT_CHAT = "2/minute"
        settings.RATE_LIMITING_ENABLED = True

        # Request 1 (OK or 400 for empty query)
        r1 = client.post("/api/v1/chat", json={"query": ""})
        assert r1.status_code == 400

        # Request 2
        r2 = client.post("/api/v1/chat", json={"query": ""})
        assert r2.status_code == 400

        # Request 3 should be 429 Too Many Requests
        r3 = client.post("/api/v1/chat", json={"query": ""})
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
        assert "Rate limit exceeded" in r3.json().get("detail", "")

    finally:
        settings.RATE_LIMIT_CHAT = original_rate
        limiter.reset()


def test_request_correlation_and_security_headers():
    """Verify RequestCorrelationMiddleware injects request ID and security headers."""
    client = TestClient(app)

    # Generated Request ID
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"

    # Preserved incoming Request ID
    custom_id = "test-custom-trace-id-12345"
    resp2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp2.headers.get("X-Request-ID") == custom_id


def test_cors_origins_configuration():
    """Verify CORS origins parsing handles comma-separated strings and wildcards."""
    s1 = Settings(CORS_ORIGINS="http://app.com,https://api.com")
    assert s1.CORS_ORIGINS == ["http://app.com", "https://api.com"]

    s2 = Settings(CORS_ORIGINS="*")
    assert s2.CORS_ORIGINS == ["*"]


def test_readiness_probe_database_check():
    """Verify /ready probe checks database health."""
    client = TestClient(app)

    # When all services healthy
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"]["database"] is True
    assert resp.json()["checks"]["faiss_index"] is True
    assert resp.json()["checks"]["chunk_corpus"] is True
    assert resp.json()["checks"]["ollama_service"] is True


def test_global_exception_sanitization():
    """Verify unhandled exceptions return 500 JSON with request_id and no stack trace."""
    client = TestClient(app, raise_server_exceptions=False)

    # Route that triggers unhandled exception
    @app.get("/test-unhandled-crash")
    def crash_endpoint():
        raise RuntimeError("InternalSecretKeyLeakException: password123")


    resp = client.get("/test-unhandled-crash")
    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data
    assert "InternalSecretKeyLeakException" not in data["detail"]
    assert "password123" not in data["detail"]
    assert "request_id" in data
    assert "X-Request-ID" in resp.headers


if __name__ == "__main__":
    test_parse_rate_limit()
    print("parse_rate_limit: PASSED")
    test_in_memory_rate_limiter_mechanism()
    print("in_memory_rate_limiter_mechanism: PASSED")
    test_rate_limiting_http_429_response()
    print("rate_limiting_http_429_response: PASSED")
    test_request_correlation_and_security_headers()
    print("request_correlation_and_security_headers: PASSED")
    test_cors_origins_configuration()
    print("cors_origins_configuration: PASSED")
    test_readiness_probe_database_check()
    print("readiness_probe_database_check: PASSED")
    test_global_exception_sanitization()
    print("global_exception_sanitization: PASSED")
    print("\nALL SECURITY & RATE LIMIT TESTS PASSED!")
