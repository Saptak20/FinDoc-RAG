import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.retrieval.hybrid_retriever import HybridRetriever
from app.engine.retrieval.reranker import CrossEncoderReranker, RerankedResult


def test_cross_encoder_reranker():
    logger.info("Initializing Cross-Encoder Reranker test...")

    # 1. Initialize HybridRetriever and CrossEncoderReranker
    hybrid_retriever = HybridRetriever()

    t0 = time.perf_counter()
    reranker = CrossEncoderReranker()
    model_load_time = time.perf_counter() - t0

    query = "EBITDA"
    top_candidates_k = 15
    final_k = 5

    # 2. Retrieve Hybrid Candidates
    candidates = hybrid_retriever.hybrid_search(
        query=query,
        dense_top_k=top_candidates_k,
        sparse_top_k=top_candidates_k,
        final_top_k=top_candidates_k,
    )

    num_candidates = len(candidates)
    assert num_candidates > 0, "No hybrid candidates returned"

    # 3. Score and Rerank candidates
    t1 = time.perf_counter()
    reranked_results = reranker.rerank(
        query=query,
        candidates=candidates,
        final_top_k=final_k,
    )
    rerank_time = time.perf_counter() - t1

    # 4. Validations
    assert len(reranked_results) == final_k, f"Expected {final_k} results, got {len(reranked_results)}"
    assert all(isinstance(r, RerankedResult) for r in reranked_results)

    prev_score = float("inf")
    for rank, res in enumerate(reranked_results, start=1):
        assert res.chunk_id is not None and len(res.chunk_id) > 0, f"Missing chunk_id at rank {rank}"
        assert isinstance(res.rerank_score, float), f"Rerank score must be float at rank {rank}"
        assert res.rerank_score <= prev_score, f"Results not in descending score order at rank {rank}: {res.rerank_score} > {prev_score}"
        assert res.rrf_score > 0.0, f"Missing or zero original RRF score at rank {rank}"
        assert len(res.retrieval_sources) > 0, f"Missing retrieval sources at rank {rank}"
        assert res.document is not None, f"Missing Document at rank {rank}"
        assert "page" in res.document.metadata, f"Missing page metadata at rank {rank}"
        prev_score = res.rerank_score

    # 5. Test final_top_k variation
    k3_results = reranker.rerank(query=query, candidates=candidates, final_top_k=3)
    assert len(k3_results) == 3, f"Expected 3 results for final_top_k=3, got {len(k3_results)}"
    assert k3_results[0].chunk_id == reranked_results[0].chunk_id

    # 6. Test empty query handling
    try:
        reranker.rerank(query="", candidates=candidates)
        assert False, "Empty query did not raise ValueError"
    except ValueError:
        pass

    try:
        reranker.rerank(query="   ", candidates=candidates)
        assert False, "Whitespace query did not raise ValueError"
    except ValueError:
        pass

    try:
        reranker.rerank(query=query, candidates=candidates, final_top_k=0)
        assert False, "final_top_k=0 did not raise ValueError"
    except ValueError:
        pass

    # 7. Test empty candidate list handling
    empty_results = reranker.rerank(query=query, candidates=[])
    assert empty_results == [], f"Expected empty list for empty candidates, got {empty_results}"

    # Print Expected Report format
    print("\n# CROSS-ENCODER RERANKER TEST")
    print()
    print(f"MODEL: {reranker.model_name}")
    print(f"DEVICE: {reranker.device}")
    print(f"QUERY: {query}")
    print()
    print(f"HYBRID CANDIDATES: {num_candidates}")
    print("CROSS-ENCODER SCORING: PASSED")
    print("CHUNK IDS PRESENT: PASSED")
    print("RERANK SCORES PRESENT: PASSED")
    print("RRF SCORES PRESERVED: PASSED")
    print("SOURCE TRACKING PRESERVED: PASSED")
    print("DESCENDING RERANK ORDER: PASSED")
    print("FINAL TOP-K: PASSED")
    print("EMPTY QUERY HANDLING: PASSED")
    print("EMPTY CANDIDATE HANDLING: PASSED")
    print()
    print("CROSS-ENCODER RERANKER TEST: PASSED\n")

    print("=" * 60)
    print(f"TOP {final_k} FINAL RERANKED RESULTS FOR QUERY: '{query}'")
    print("=" * 60)
    for rank, res in enumerate(reranked_results, start=1):
        preview = res.document.page_content.replace("\n", " ")[:130]
        sources_str = ", ".join(res.retrieval_sources)
        print(f"Rank {rank}:")
        print(f"  Chunk ID           : {res.chunk_id}")
        print(f"  Cross-Encoder Score: {res.rerank_score:.6f}")
        print(f"  RRF Score          : {res.rrf_score:.6f}")
        print(f"  Sources            : [{sources_str}]")
        print(f"  Page               : {res.document.metadata.get('page')}")
        print(f"  Preview            : {preview}...")
        print()

    print("=" * 60)
    print("PERFORMANCE METRICS:")
    print("=" * 60)
    print(f"Model Loading Time : {model_load_time:.2f} seconds")
    print(f"Candidates Reranked: {num_candidates}")
    print(f"Reranking Time     : {rerank_time:.4f} seconds ({rerank_time*1000:.1f} ms)")
    print()


if __name__ == "__main__":
    test_cross_encoder_reranker()
