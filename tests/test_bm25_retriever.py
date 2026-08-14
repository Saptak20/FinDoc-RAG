import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.retrieval.bm25_retriever import BM25Retriever


def test_bm25_retriever():
    logger.info("Initializing BM25 retriever test...")

    # 1. Initialize BM25 retriever and verify load & index build
    retriever = BM25Retriever()
    
    # 2. Check total corpus chunks
    chunk_count = retriever.chunk_count
    assert chunk_count == 2710, f"Expected 2710 chunks, got {chunk_count}"
    
    # 3. Test exact financial term retrieval
    query = "EBITDA"
    top_k = 5
    results = retriever.bm25_search(query=query, k=top_k)
    
    # 4. Check results returned
    assert len(results) == top_k, f"Expected {top_k} results, got {len(results)}"
    
    # 5. Check chunk_id, scores, metadata, and score ordering
    prev_score = float("inf")
    for rank, (doc, score) in enumerate(results, start=1):
        chunk_id = doc.metadata.get("chunk_id")
        source = doc.metadata.get("source")
        page = doc.metadata.get("page")
        chunk_index = doc.metadata.get("chunk_index")
        
        assert chunk_id is not None and len(chunk_id) > 0, f"Missing chunk_id at rank {rank}"
        assert source is not None, f"Missing source at rank {rank}"
        assert page is not None, f"Missing page at rank {rank}"
        assert chunk_index is not None, f"Missing chunk_index at rank {rank}"
        assert isinstance(score, float), f"Score is not a float at rank {rank}"
        assert score > 0.0, f"Expected positive score for exact match, got {score}"
        assert score <= prev_score, f"Results not ordered by score: {score} > {prev_score}"
        prev_score = score

    # 6. Test top_k variation
    k3_results = retriever.bm25_search(query=query, k=3)
    assert len(k3_results) == 3, f"Expected 3 results for k=3, got {len(k3_results)}"
    assert k3_results[0][0].metadata["chunk_id"] == results[0][0].metadata["chunk_id"]

    # 7. Test empty/invalid query handling
    try:
        retriever.bm25_search("")
        assert False, "Empty query did not raise ValueError"
    except ValueError:
        pass

    try:
        retriever.bm25_search("   ")
        assert False, "Whitespace query did not raise ValueError"
    except ValueError:
        pass

    try:
        retriever.bm25_search(query=query, k=0)
        assert False, "k=0 did not raise ValueError"
    except ValueError:
        pass

    # Query with no alphanumeric tokens returns empty list
    non_token_results = retriever.bm25_search("!@#$%^&*")
    assert len(non_token_results) == 0, f"Expected 0 results for non-token query, got {len(non_token_results)}"

    print("\n" + "=" * 50)
    print("# BM25 RETRIEVER TEST")
    print("=" * 50)
    print(f"CORPUS CHUNKS: {chunk_count}")
    print("INDEX BUILD: PASSED")
    print(f"QUERY: {query}")
    print(f"RESULTS RETURNED: {len(results)}")
    print("RESULTS HAVE CHUNK IDS: PASSED")
    print("RESULTS HAVE BM25 SCORES: PASSED")
    print("RESULTS ORDERED BY SCORE: PASSED")
    print("TOP-K TEST: PASSED")
    print("METADATA TEST: PASSED")
    print("EXACT TERM RETRIEVAL: PASSED")
    print("\nBM25 RETRIEVER TEST: PASSED\n")

    print("=" * 50)
    print("TOP 3 RETRIEVAL SAMPLES:")
    print("=" * 50)
    for rank, (doc, score) in enumerate(results[:3], start=1):
        preview = doc.page_content.replace("\n", " ")[:140]
        print(f"Rank {rank}:")
        print(f"  BM25 Score : {score:.4f}")
        print(f"  Chunk ID   : {doc.metadata.get('chunk_id')}")
        print(f"  Source     : {doc.metadata.get('source')}")
        print(f"  Page       : {doc.metadata.get('page')}")
        print(f"  Preview    : {preview}...")
        print()


if __name__ == "__main__":
    test_bm25_retriever()
