import json
import os
import sys
import time
from typing import Any, Dict, List, Set, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.retrieval.bm25_retriever import BM25Retriever
from app.engine.retrieval.hybrid_retriever import HybridRetriever
from app.engine.retrieval.rank_fusion import RankFusion
from app.engine.retrieval.reranker import CrossEncoderReranker
from app.engine.retrieval.retriever import DenseRetriever


def is_match(retrieved_doc: Any, expected_sources: List[Dict[str, Any]]) -> bool:
    """
    Check if a retrieved Document matches any expected (source_file, page).
    """
    metadata = getattr(retrieved_doc, "metadata", {})
    raw_source = metadata.get("source", "")
    retrieved_filename = os.path.basename(raw_source)
    retrieved_page = metadata.get("page")

    for exp in expected_sources:
        exp_file = exp.get("source", "")
        exp_page = exp.get("page")

        if exp_file == retrieved_filename and exp_page == retrieved_page:
            return True

    return False


def calculate_recall_at_k(
    results_list: List[List[Any]],
    dataset: List[Dict[str, Any]],
    k: int,
) -> float:
    """
    Calculate Recall@K across all dataset queries.
    Recall@K = (Queries with >= 1 relevant document in top K) / Total Queries
    """
    hits = 0
    total = len(dataset)

    for results, item in zip(results_list, dataset):
        expected = item.get("expected_sources", [])
        top_k_results = results[:k]

        has_hit = False
        for res in top_k_results:
            # Handle FusedResult, RerankedResult, or (Document, score)
            doc = getattr(res, "document", None)
            if doc is None:
                if isinstance(res, tuple):
                    doc = res[0]
                else:
                    doc = res

            if is_match(doc, expected):
                has_hit = True
                break

        if has_hit:
            hits += 1

    return (hits / total) * 100.0 if total > 0 else 0.0


def run_retrieval_evaluation():
    dataset_path = os.path.join(PROJECT_ROOT, "evaluation", "dataset.json")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    logger.info(f"Loaded {len(dataset)} evaluation questions from {dataset_path}")

    # Initialize all retrieval components
    logger.info("Initializing DenseRetriever (FAISS)...")
    dense_retriever = DenseRetriever()

    logger.info("Initializing BM25Retriever...")
    bm25_retriever = BM25Retriever()

    logger.info("Initializing HybridRetriever...")
    hybrid_retriever = HybridRetriever(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
    )

    logger.info("Initializing CrossEncoderReranker...")
    reranker = CrossEncoderReranker()

    faiss_results_all = []
    bm25_results_all = []
    hybrid_results_all = []
    reranked_results_all = []

    dense_latencies = []
    bm25_latencies = []
    hybrid_latencies = []
    rerank_latencies = []

    logger.info(f"Running retrieval evaluation across {len(dataset)} queries...")

    for item in dataset:
        q = item["question"]

        # 1. FAISS Only
        t0 = time.perf_counter()
        faiss_res = dense_retriever.dense_search(query=q, k=10)
        dense_latencies.append(time.perf_counter() - t0)
        faiss_results_all.append(faiss_res)

        # 2. BM25 Only
        t0 = time.perf_counter()
        bm25_res = bm25_retriever.bm25_search(query=q, k=10)
        bm25_latencies.append(time.perf_counter() - t0)
        bm25_results_all.append(bm25_res)

        # 3. Hybrid (RRF)
        t0 = time.perf_counter()
        hybrid_res = hybrid_retriever.hybrid_search(
            query=q,
            dense_top_k=15,
            sparse_top_k=15,
            final_top_k=10,
        )
        hybrid_latencies.append(time.perf_counter() - t0)
        hybrid_results_all.append(hybrid_res)

        # 4. Hybrid + Cross-Encoder Reranker
        t0 = time.perf_counter()
        reranked_res = reranker.rerank(
            query=q,
            candidates=hybrid_res,
            final_top_k=5,
        )
        rerank_latencies.append(time.perf_counter() - t0)
        reranked_results_all.append(reranked_res)

    k_values = [1, 3, 5, 10]

    metrics = {
        "FAISS (Dense)": {k: calculate_recall_at_k(faiss_results_all, dataset, k) for k in k_values},
        "BM25 (Sparse)": {k: calculate_recall_at_k(bm25_results_all, dataset, k) for k in k_values},
        "Hybrid (RRF)": {k: calculate_recall_at_k(hybrid_results_all, dataset, k) for k in k_values},
        "Hybrid + Reranker": {k: calculate_recall_at_k(reranked_results_all, dataset, k) for k in [1, 3, 5]},
    }

    avg_dense_lat = sum(dense_latencies) / len(dense_latencies)
    avg_bm25_lat = sum(bm25_latencies) / len(bm25_latencies)
    avg_hybrid_lat = sum(hybrid_latencies) / len(hybrid_latencies)
    avg_rerank_lat = sum(rerank_latencies) / len(rerank_latencies)

    print("\n" + "=" * 70)
    print("RETRIEVAL EVALUATION & STRATEGY COMPARISON")
    print("=" * 70)
    print(f"Evaluation Queries: {len(dataset)}")
    print()
    print(f"{'METHOD':<22} | {'RECALL@1':<10} | {'RECALL@3':<10} | {'RECALL@5':<10} | {'RECALL@10':<10}")
    print("-" * 70)

    for method, scores in metrics.items():
        r1 = f"{scores.get(1, 0.0):.1f}%"
        r3 = f"{scores.get(3, 0.0):.1f}%"
        r5 = f"{scores.get(5, 0.0):.1f}%"
        r10 = f"{scores.get(10, 0.0):.1f}%" if 10 in scores else "N/A"
        print(f"{method:<22} | {r1:<10} | {r3:<10} | {r5:<10} | {r10:<10}")

    print("-" * 70)
    print()
    print("LATENCY BASELINE (RETRIEVAL):")
    print(f"  Average FAISS Dense Latency    : {avg_dense_lat * 1000:.2f} ms")
    print(f"  Average BM25 Sparse Latency    : {avg_bm25_lat * 1000:.2f} ms")
    print(f"  Average Hybrid (RRF) Latency   : {avg_hybrid_lat * 1000:.2f} ms")
    print(f"  Average Cross-Encoder Latency  : {avg_rerank_lat * 1000:.2f} ms")
    print(f"  Average Total Retrieval Latency: {(avg_hybrid_lat + avg_rerank_lat) * 1000:.2f} ms")
    print("=" * 70 + "\n")

    return metrics


if __name__ == "__main__":
    run_retrieval_evaluation()
