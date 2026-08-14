import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient

from app.api.dependencies import get_rag_pipeline
from app.core.logger import logger
from app.main import app


def test_api():
    logger.info("Initializing FastAPI API test suite...")

    client = TestClient(app)

    # 1. Test Root and Health Endpoints
    root_resp = client.get("/")
    assert root_resp.status_code == 200, f"Root endpoint failed: {root_resp.status_code}"

    health_resp = client.get("/health")
    assert health_resp.status_code == 200, f"Health endpoint failed: {health_resp.status_code}"
    health_data = health_resp.json()
    assert health_data.get("status") == "healthy", f"Health status not healthy: {health_data}"

    # 2. Test OpenAPI Documentation Schema
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200, "OpenAPI schema endpoint failed"
    openapi_data = openapi_resp.json()
    paths = openapi_data.get("paths", {})
    assert "/api/v1/chat" in paths, "OpenAPI missing /api/v1/chat route"
    assert "/health" in paths, "OpenAPI missing /health route"

    # 3. Test Empty Query Validation (HTTP 400)
    empty_resp = client.post("/api/v1/chat", json={"query": ""})
    assert empty_resp.status_code == 400, f"Expected HTTP 400 for empty query, got {empty_resp.status_code}"

    whitespace_resp = client.post("/api/v1/chat", json={"query": "    "})
    assert whitespace_resp.status_code == 400, f"Expected HTTP 400 for whitespace query, got {whitespace_resp.status_code}"

    # 4. Test Invalid Request Body (HTTP 422)
    invalid_body_resp = client.post("/api/v1/chat", json={"invalid_field": 123})
    assert invalid_body_resp.status_code == 422, f"Expected HTTP 422 for invalid body, got {invalid_body_resp.status_code}"

    invalid_topk_resp = client.post("/api/v1/chat", json={"query": "Valid query", "final_top_k": 0})
    assert invalid_topk_resp.status_code == 422, f"Expected HTTP 422 for final_top_k=0, got {invalid_topk_resp.status_code}"

    # 5. Test Pipeline Error Handling (HTTP 500)
    class FailingPipeline:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("Simulated internal pipeline error")

    app.dependency_overrides[get_rag_pipeline] = lambda: FailingPipeline()
    error_resp = client.post("/api/v1/chat", json={"query": "Test error"})
    assert error_resp.status_code == 500, f"Expected HTTP 500 for pipeline failure, got {error_resp.status_code}"
    assert "error occurred" in error_resp.json().get("detail", "").lower()
    app.dependency_overrides.clear()

    # 6. Real Live Integration Test with Chat Endpoint
    query = "What was Tata Steel's EBITDA margin in FY2023-24?"
    payload = {
        "query": query,
        "dense_top_k": 10,
        "sparse_top_k": 10,
        "final_top_k": 3,
    }

    t0 = time.perf_counter()
    chat_resp = client.post("/api/v1/chat", json=payload)
    elapsed_time = time.perf_counter() - t0

    assert chat_resp.status_code == 200, f"Chat endpoint failed with status {chat_resp.status_code}: {chat_resp.text}"

    data = chat_resp.json()

    # Assert response schema structure
    assert data.get("query") == query, "Query mismatch in response"
    assert data.get("answer") and len(data["answer"].strip()) > 0, "Empty answer returned"
    
    sources = data.get("sources", [])
    assert len(sources) > 0, "No sources returned in response"
    for s in sources:
        assert s.get("source") == "OTC_TATLY_2024.pdf", f"Invalid source filename: {s.get('source')}"
        assert isinstance(s.get("page"), int), f"Invalid page number: {s.get('page')}"
        assert s.get("chunk_id") and len(s.get("chunk_id")) > 0, f"Missing chunk_id: {s}"

    metrics = data.get("metrics", {})
    assert metrics.get("retrieval_candidates", 0) > 0, "Candidate count zero"
    assert metrics.get("reranked_chunks", 0) > 0, "Reranked count zero"
    assert metrics.get("latency_seconds", 0) > 0, "Latency zero"

    # Print Expected Test Report Format
    print("\nFASTAPI API TEST")
    print("==============================")
    print()
    print("APPLICATION IMPORT: PASSED")
    print("HEALTH ENDPOINT: PASSED")
    print("CHAT ENDPOINT: PASSED")
    print("RAG PIPELINE INTEGRATION: PASSED")
    print("ANSWER RESPONSE: PASSED")
    print("SOURCE METADATA: PASSED")
    print("METRICS: PASSED")
    print("EMPTY QUERY HANDLING: PASSED")
    print("INVALID REQUEST HANDLING: PASSED")
    print("PIPELINE ERROR HANDLING: PASSED")
    print("OPENAPI DOCUMENTATION: PASSED")
    print()
    print("FASTAPI API TEST: PASSED\n")

    print("=" * 60)
    print("REQUEST:")
    print(payload)
    print()
    print(f"RESPONSE STATUS: {chat_resp.status_code}")
    print()
    print("ANSWER:")
    print(data.get("answer"))
    print()
    print("SOURCES:")
    for idx, src in enumerate(sources, start=1):
        print(f"  {idx}. Source: {src['source']} | Page: {src['page']} | Chunk: {src['chunk_id']}")
    print()
    print("METRICS:")
    print(f"  Retrieval Candidates: {metrics.get('retrieval_candidates')}")
    print(f"  Reranked Chunks     : {metrics.get('reranked_chunks')}")
    print(f"  Latency (Reported)  : {metrics.get('latency_seconds')} seconds")
    print(f"  Latency (End-to-End): {elapsed_time:.2f} seconds")
    print("=" * 60)
    print()


if __name__ == "__main__":
    test_api()
