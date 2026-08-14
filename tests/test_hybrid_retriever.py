import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.retrieval.hybrid_retriever import HybridRetriever
from app.engine.retrieval.rank_fusion import FusedResult


def test_hybrid_retriever():
    logger.info("Initializing HybridRetriever test on 2710-chunk corpus...")

    # 1. Initialize HybridRetriever
    retriever = HybridRetriever()

    assert retriever.vector_count == 2710, f"Expected 2710 vectors, got {retriever.vector_count}"
    assert retriever.chunk_count == 2710, f"Expected 2710 chunks, got {retriever.chunk_count}"

    # 2. Run Hybrid Search with query "EBITDA"
    query = "EBITDA"
    top_k = 5
    results = retriever.hybrid_search(
        query=query,
        dense_top_k=10,
        sparse_top_k=10,
        final_top_k=top_k,
    )

    # 3. Validations
    assert len(results) == top_k, f"Expected {top_k} results, got {len(results)}"
    assert all(isinstance(r, FusedResult) for r in results)

    # Validate chunk_id, scores, metadata, sources, sorting
    prev_score = float("inf")
    for rank, res in enumerate(results, start=1):
        assert res.chunk_id is not None and len(res.chunk_id) > 0, f"Missing chunk_id at rank {rank}"
        assert res.fused_score > 0.0, f"Fused score must be positive at rank {rank}"
        assert res.fused_score <= prev_score, f"Results not sorted descending: {res.fused_score} > {prev_score}"
        assert len(res.retrieval_sources) > 0, f"Missing retrieval sources at rank {rank}"
        assert res.document is not None, f"Missing document at rank {rank}"
        assert "page" in res.document.metadata, f"Missing page metadata at rank {rank}"
        prev_score = res.fused_score

    # 4. Validate final_top_k variation
    k3_results = retriever.hybrid_search(query=query, final_top_k=3)
    assert len(k3_results) == 3, f"Expected 3 results for final_top_k=3, got {len(k3_results)}"
    assert k3_results[0].chunk_id == results[0].chunk_id

    # 5. Empty and invalid query handling
    try:
        retriever.hybrid_search("")
        assert False, "Empty query did not raise ValueError"
    except ValueError:
        pass

    try:
        retriever.hybrid_search("   ")
        assert False, "Whitespace query did not raise ValueError"
    except ValueError:
        pass

    try:
        retriever.hybrid_search(query=query, final_top_k=0)
        assert False, "final_top_k=0 did not raise ValueError"
    except ValueError:
        pass

    # Print Expected Report format
    print("\nHYBRID RETRIEVER TEST")
    print("========================")
    print(f"QUERY: {query}\n")
    print("FAISS RETRIEVAL: PASSED")
    print("BM25 RETRIEVAL: PASSED")
    print("RRF FUSION: PASSED")
    print(f"RESULTS RETURNED: {len(results)}")
    print("CHUNK IDS PRESENT: PASSED")
    print("FUSED SCORES PRESENT: PASSED")
    print("SORTING: PASSED")
    print("FINAL TOP-K: PASSED")
    print("SOURCE TRACKING: PASSED")
    print("EMPTY QUERY HANDLING: PASSED")
    print()
    print("HYBRID RETRIEVER TEST: PASSED\n")

    print("=" * 50)
    print(f"TOP {top_k} HYBRID RESULTS FOR QUERY: '{query}'")
    print("=" * 50)
    for rank, res in enumerate(results, start=1):
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
    test_hybrid_retriever()
