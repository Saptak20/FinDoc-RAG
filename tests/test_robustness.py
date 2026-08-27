import os
import sys
import tempfile
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.engine.ingestion.chunk_store import ChunkStore
from app.engine.pipelines import RAGPipeline
from app.engine.retrieval.bm25_retriever import BM25Retriever
from app.engine.retrieval.hybrid_retriever import HybridRetriever
from app.engine.retrieval.rank_fusion import RankFusion
from app.engine.retrieval.reranker import CrossEncoderReranker
from app.engine.retrieval.retriever import DenseRetriever
from app.main import app


def test_robustness_empty_query():
    pipeline = RAGPipeline()
    res = pipeline.invoke("")
    assert res.get("error") is not None
    assert "empty" in res.get("error", "").lower()

    res_ws = pipeline.invoke("   \n\t  ")
    assert res_ws.get("error") is not None


def test_robustness_extremely_long_query():
    pipeline = RAGPipeline()
    # 5,000 character long repeated query
    long_query = "What is the EBITDA of Tata Steel in FY2023-24? " * 100
    res = pipeline.invoke(long_query, dense_top_k=5, sparse_top_k=5, final_top_k=2)
    assert res.get("error") is None
    assert len(res.get("answer", "")) > 0


def test_robustness_invalid_top_k():
    pipeline = RAGPipeline()
    try:
        pipeline.invoke("What is EBITDA?", dense_top_k=0)
        assert False, "dense_top_k=0 did not raise ValueError"
    except ValueError:
        pass

    try:
        pipeline.invoke("What is EBITDA?", final_top_k=-5)
        assert False, "final_top_k=-5 did not raise ValueError"
    except ValueError:
        pass


def test_robustness_missing_chunks_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        retriever = BM25Retriever.__new__(BM25Retriever)
        retriever.persist_dir = tmpdir
        retriever.filename = "non_existent.jsonl"
        retriever.chunk_store = ChunkStore(persist_dir=tmpdir, filename="non_existent.jsonl")
        try:
            retriever._load_and_index()
            assert False, "Expected FileNotFoundError for missing chunks.jsonl"
        except FileNotFoundError:
            pass


def test_robustness_empty_corpus():
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_file = os.path.join(tmpdir, "chunks.jsonl")
        with open(empty_file, "w") as f:
            f.write("\n\n")  # Empty lines only

        store = ChunkStore(persist_dir=tmpdir, filename="chunks.jsonl")
        try:
            store.load_chunks()
            assert False, "Expected ValueError for empty chunk corpus"
        except ValueError:
            pass


def test_robustness_missing_faiss_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            DenseRetriever(persist_dir=tmpdir)
            assert False, "Expected FileNotFoundError for missing FAISS index"
        except FileNotFoundError:
            pass


def test_robustness_reranker_edge_cases():
    reranker = CrossEncoderReranker()
    # Empty candidates
    assert reranker.rerank("Query", candidates=[]) == []

    # Invalid empty query
    try:
        reranker.rerank("", candidates=[Document(page_content="Text", metadata={"chunk_id": "c1"})])
        assert False, "Expected ValueError for empty query in reranker"
    except ValueError:
        pass


def test_robustness_no_context_handling():
    pipeline = RAGPipeline()
    # Query with random gibberish that yields no exact match in context
    gibberish_query = "xyz987qwe123 NonExistentMetricAndEntityAlphaBetaGamma"
    res = pipeline.invoke(gibberish_query, dense_top_k=3, sparse_top_k=3, final_top_k=2)
    assert res.get("answer") is not None
    assert len(res["answer"]) > 0


def test_robustness_api_malformed_requests():
    client = TestClient(app)

    # Missing query field
    r1 = client.post("/api/v1/chat", json={})
    assert r1.status_code == 422

    # Wrong data types
    r2 = client.post("/api/v1/chat", json={"query": 12345})
    # FastAPI can coerce int to string or return 422; if coerced, query becomes "12345"
    assert r2.status_code in [200, 422]

    # Negative integer in top_k
    r3 = client.post("/api/v1/chat", json={"query": "Test", "final_top_k": -1})
    assert r3.status_code == 422


if __name__ == "__main__":
    print("Running Robustness Test Suite...")
    test_robustness_empty_query()
    print("Empty query test: PASSED")
    test_robustness_extremely_long_query()
    print("Extremely long query test: PASSED")
    test_robustness_invalid_top_k()
    print("Invalid top_k test: PASSED")
    test_robustness_missing_chunks_jsonl()
    print("Missing chunks.jsonl test: PASSED")
    test_robustness_empty_corpus()
    print("Empty corpus test: PASSED")
    test_robustness_missing_faiss_index()
    print("Missing FAISS index test: PASSED")
    test_robustness_reranker_edge_cases()
    print("Reranker edge cases test: PASSED")
    test_robustness_no_context_handling()
    print("No-context handling test: PASSED")
    test_robustness_api_malformed_requests()
    print("API malformed requests test: PASSED")
    print("\nALL ROBUSTNESS TESTS PASSED!")
