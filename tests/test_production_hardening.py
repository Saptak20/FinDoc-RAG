import os
import sys
import pytest
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_rag_pipeline
from app.core.config import Settings
from app.db.session import log_query_to_db
from app.main import app


def test_hardening_config_validation():
    """Verify Settings rejects invalid configurations."""
    # Invalid log level
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="INVALID_LEVEL")

    # Overlap greater than chunk size
    with pytest.raises(ValidationError):
        Settings(CHUNK_SIZE=500, CHUNK_OVERLAP=600)

    # Positive validations
    valid_settings = Settings(CHUNK_SIZE=1000, CHUNK_OVERLAP=200, LOG_LEVEL="DEBUG")
    assert valid_settings.CHUNK_SIZE == 1000
    assert valid_settings.CHUNK_OVERLAP == 200
    assert valid_settings.LOG_LEVEL == "DEBUG"


def test_hardening_resource_reuse():
    """Verify get_rag_pipeline provides a singleton instance."""
    p1 = get_rag_pipeline()
    p2 = get_rag_pipeline()
    assert p1 is p2, "get_rag_pipeline did not reuse singleton instance"


def test_hardening_health_and_ready_endpoints():
    """Verify /health and /ready endpoints return proper status."""
    client = TestClient(app)

    # Liveness probe
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json().get("status") == "healthy"

    # Readiness probe
    ready_resp = client.get("/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert ready_data.get("status") == "ready"
    assert ready_data["checks"]["faiss_index"] is True
    assert ready_data["checks"]["chunk_corpus"] is True
    assert ready_data["checks"]["ollama_service"] is True


def test_hardening_readiness_missing_artifacts():
    """Verify /ready returns 503 if vector store path is invalid."""
    client = TestClient(app)
    with patch("os.path.exists", return_value=False):
        resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data.get("status") == "not_ready"
        assert data["checks"]["faiss_index"] is False


def test_hardening_database_logging_safe_fallback():
    """Verify log_query_to_db does not raise unhandled exceptions on DB errors."""
    import asyncio
    # Calling log_query_to_db even when DB is unreachable must handle error safely
    asyncio.run(log_query_to_db("Test Query", "Test Response", 123.45))


def test_hardening_error_sanitization():
    """Verify 500 internal errors do not leak stack traces or internal paths to clients."""
    client = TestClient(app)

    class CrashingPipeline:
        def invoke(self, *args, **kwargs):
            raise Exception("SecretInternalDatabasePasswordOrKey at /var/secrets/key.pem")

    app.dependency_overrides[get_rag_pipeline] = lambda: CrashingPipeline()

    resp = client.post("/api/v1/chat", json={"query": "Test crash"})
    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert "/var/secrets" not in detail
    assert "SecretInternal" not in detail
    assert detail == "An error occurred while processing the financial query."

    app.dependency_overrides.clear()


if __name__ == "__main__":
    print("Running Production Hardening Test Suite...")
    test_hardening_config_validation()
    print("Config validation: PASSED")
    test_hardening_resource_reuse()
    print("Resource reuse: PASSED")
    test_hardening_health_and_ready_endpoints()
    print("Health and Ready endpoints: PASSED")
    test_hardening_readiness_missing_artifacts()
    print("Readiness missing artifacts: PASSED")
    test_hardening_database_logging_safe_fallback()
    print("Database logging safe fallback: PASSED")
    test_hardening_error_sanitization()
    print("Error sanitization: PASSED")
    print("\nALL PRODUCTION HARDENING TESTS PASSED!")
