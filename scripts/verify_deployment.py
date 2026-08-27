#!/usr/bin/env python3
"""
Deployment verification script for FinDoc-RAG.
Tests /health, /ready, and POST /api/v1/chat against the running local/container deployment.
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8000"


def verify_deployment():
    print("=" * 60)
    print("FINDOC-RAG DEPLOYMENT VERIFICATION")
    print("=" * 60)

    # 1. Test /health
    print("\n[1/3] Testing /health endpoint...")
    try:
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r_health.status_code == 200, f"Expected 200, got {r_health.status_code}"
        health_json = r_health.json()
        assert health_json.get("status") == "healthy", f"Unexpected payload: {health_json}"
        print("  -> /health: PASSED (200 OK, status: healthy)")
    except Exception as e:
        print(f"  -> /health: FAILED ({e})")
        sys.exit(1)

    # 2. Test /ready
    print("\n[2/3] Testing /ready endpoint...")
    try:
        r_ready = requests.get(f"{BASE_URL}/ready", timeout=5)
        assert r_ready.status_code == 200, f"Expected 200, got {r_ready.status_code}"
        ready_json = r_ready.json()
        assert ready_json.get("status") == "ready", f"Unexpected payload: {ready_json}"
        checks = ready_json.get("checks", {})
        assert checks.get("faiss_index") is True, "FAISS index check failed"
        assert checks.get("chunk_corpus") is True, "Chunk corpus check failed"
        assert checks.get("ollama_service") is True, "Ollama service check failed"
        print("  -> /ready: PASSED (200 OK, all dependency checks passed)")
    except Exception as e:
        print(f"  -> /ready: FAILED ({e})")
        sys.exit(1)

    # 3. Test POST /api/v1/chat
    print("\n[3/3] Testing live POST /api/v1/chat endpoint...")
    payload = {
        "query": "What was Tata Steel's EBITDA margin in FY2023-24?",
        "dense_top_k": 10,
        "sparse_top_k": 10,
        "final_top_k": 3,
    }

    t0 = time.perf_counter()
    try:
        r_chat = requests.post(f"{BASE_URL}/api/v1/chat", json=payload, timeout=60)
        latency = time.perf_counter() - t0
        assert r_chat.status_code == 200, f"Expected 200, got {r_chat.status_code}: {r_chat.text}"
        chat_json = r_chat.json()
        
        answer = chat_json.get("answer", "")
        sources = chat_json.get("sources", [])
        metrics = chat_json.get("metrics", {})

        assert len(answer.strip()) > 0, "Empty answer returned"
        assert len(sources) > 0, "No sources returned"
        assert "22%" in answer or "EBITDA" in answer, f"Unexpected answer content: {answer}"

        print(f"  -> /api/v1/chat: PASSED (200 OK, latency: {latency:.2f}s)")
        print(f"     Answer : {answer}")
        print(f"     Sources: {len(sources)} cited (Top: {sources[0].get('source')} p.{sources[0].get('page')})")
        print(f"     Metrics: {metrics}")
    except Exception as e:
        print(f"  -> /api/v1/chat: FAILED ({e})")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL DEPLOYMENT CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    verify_deployment()
