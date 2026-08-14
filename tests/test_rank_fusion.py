import os
import sys
import math

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langchain_core.documents import Document
from app.engine.retrieval.rank_fusion import (
    FusedResult,
    RankFusion,
    reciprocal_rank_fusion,
)
from app.engine.retrieval.retriever import DenseRetriever
from app.engine.retrieval.bm25_retriever import BM25Retriever


def test_deterministic_mock_rank_fusion():
    """Verify exact mathematical correctness, deduplication, source tracking, and error handling."""
    k = 60
    fusion = RankFusion(rrf_k=k)

    doc_a = Document(page_content="Content A", metadata={"chunk_id": "chunk_A", "source": "test.pdf", "page": 1})
    doc_b = Document(page_content="Content B", metadata={"chunk_id": "chunk_B", "source": "test.pdf", "page": 2})
    doc_c = Document(page_content="Content C", metadata={"chunk_id": "chunk_C", "source": "test.pdf", "page": 3})
    doc_d = Document(page_content="Content D", metadata={"chunk_id": "chunk_D", "source": "test.pdf", "page": 4})

    # FAISS: [A (rank 1), B (rank 2)]
    # BM25:  [B (rank 1), C (rank 2), D (rank 3)]
    dense_results = [(doc_a, 0.15), (doc_b, 0.25)]
    sparse_results = [(doc_b, 8.5), (doc_c, 5.2), (doc_d, 3.1)]

    # Theoretical Scores:
    # chunk_A: 1/(60+1) = 1/61 ≈ 0.0163934426
    # chunk_B: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ≈ 0.0161290323 + 0.0163934426 = 0.0325224749
    # chunk_C: 1/(60+2) = 1/62 ≈ 0.0161290323
    # chunk_D: 1/(60+3) = 1/63 ≈ 0.0158730159

    fused = fusion.fuse(dense_results, sparse_results)

    # 1. Total unique results
    assert len(fused) == 4, f"Expected 4 unique fused results, got {len(fused)}"

    # 2. Ranking order: B (0.0325) > A (0.01639) > C (0.01613) > D (0.01587)
    expected_order = ["chunk_B", "chunk_A", "chunk_C", "chunk_D"]
    actual_order = [r.chunk_id for r in fused]
    assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"

    # 3. Score mathematical verification
    score_b_expected = 1.0 / (k + 2) + 1.0 / (k + 1)
    score_a_expected = 1.0 / (k + 1)
    score_c_expected = 1.0 / (k + 2)
    score_d_expected = 1.0 / (k + 3)

    assert math.isclose(fused[0].fused_score, score_b_expected, rel_tol=1e-6)
    assert math.isclose(fused[1].fused_score, score_a_expected, rel_tol=1e-6)
    assert math.isclose(fused[2].fused_score, score_c_expected, rel_tol=1e-6)
    assert math.isclose(fused[3].fused_score, score_d_expected, rel_tol=1e-6)

    # 4. Source tracking
    assert sorted(fused[0].retrieval_sources) == ["bm25", "faiss"]
    assert fused[1].retrieval_sources == ["faiss"]
    assert fused[2].retrieval_sources == ["bm25"]
    assert fused[3].retrieval_sources == ["bm25"]

    # 5. Top-K slicing
    fused_top2 = fusion.fuse(dense_results, sparse_results, top_k=2)
    assert len(fused_top2) == 2
    assert fused_top2[0].chunk_id == "chunk_B"
    assert fused_top2[1].chunk_id == "chunk_A"

    # 6. Empty handling
    assert fusion.fuse([], []) == []
    assert len(fusion.fuse(dense_results, [])) == 2
    assert len(fusion.fuse([], sparse_results)) == 3

    # 7. Error handling
    try:
        RankFusion(rrf_k=0)
        assert False, "rrf_k=0 did not raise ValueError"
    except ValueError:
        pass

    try:
        fusion.fuse(dense_results, sparse_results, top_k=0)
        assert False, "top_k=0 did not raise ValueError"
    except ValueError:
        pass


def run_full_integration_test():
    """Run rank fusion test with real FAISS and BM25 retrievers over 2710 chunks."""
    # 1. Run deterministic mock test
    test_deterministic_mock_rank_fusion()

    # 2. Integration test with real FAISS and BM25
    dense_retriever = DenseRetriever()
    bm25_retriever = BM25Retriever()

    query = "EBITDA"
    top_k_retrieve = 10
    top_k_fused = 10

    dense_results = dense_retriever.dense_search(query=query, k=top_k_retrieve)
    bm25_results = bm25_retriever.bm25_search(query=query, k=top_k_retrieve)

    faiss_count = len(dense_results)
    bm25_count = len(bm25_results)

    fusion = RankFusion(rrf_k=60)
    fused_results = fusion.fuse(
        dense_results=dense_results,
        sparse_results=bm25_results,
        top_k=top_k_fused,
    )

    all_chunk_ids = set()
    for d, _ in dense_results:
        all_chunk_ids.add(d.metadata["chunk_id"])
    for d, _ in bm25_results:
        all_chunk_ids.add(d.metadata["chunk_id"])

    total_candidates = len(dense_results) + len(bm25_results)
    unique_candidates_count = len(all_chunk_ids)
    duplicates_merged_count = total_candidates - unique_candidates_count

    # Assertions on real results
    assert len(fused_results) <= top_k_fused
    assert all(isinstance(r, FusedResult) for r in fused_results)
    assert all(r.chunk_id for r in fused_results)
    assert all(r.fused_score > 0 for r in fused_results)

    # Check sorting
    for i in range(len(fused_results) - 1):
        assert fused_results[i].fused_score >= fused_results[i + 1].fused_score

    print("RANK FUSION TEST")
    print("========================")
    print(f"FAISS RESULTS: {faiss_count}")
    print(f"BM25 RESULTS: {bm25_count}")
    print(f"UNIQUE FUSED RESULTS: {unique_candidates_count}")
    print(f"DUPLICATES MERGED: {duplicates_merged_count}")
    print("RRF CALCULATION: PASSED")
    print("DEDUPLICATION: PASSED")
    print("SOURCE TRACKING: PASSED")
    print("SORTING: PASSED")
    print("TOP-K: PASSED")
    print("EMPTY INPUT: PASSED")
    print()
    print("RANK FUSION TEST: PASSED")
    print()
    print("=" * 50)
    print(f"TOP 5 FUSED RESULTS FOR QUERY: '{query}'")
    print("=" * 50)
    for rank, res in enumerate(fused_results[:5], start=1):
        preview = res.document.page_content.replace("\n", " ")[:120]
        sources_str = ", ".join(res.retrieval_sources)
        print(f"Rank {rank}:")
        print(f"  Chunk ID : {res.chunk_id}")
        print(f"  RRF Score: {res.fused_score:.6f}")
        print(f"  Sources  : [{sources_str}]")
        print(f"  Page     : {res.document.metadata.get('page')}")
        print(f"  Preview  : {preview}...")
        print()


if __name__ == "__main__":
    run_full_integration_test()
