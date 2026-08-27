import json
import os
import sys
import time
from typing import Any, Dict, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.pipelines import RAGPipeline


def is_source_attributed(sources: List[Dict[str, Any]], expected_sources: List[Dict[str, Any]]) -> bool:
    """Check if any of the cited sources matches the expected page/document."""
    for src in sources:
        src_file = src.get("filename", "")
        src_page = src.get("page")
        for exp in expected_sources:
            if src_file == exp.get("source") and src_page == exp.get("page"):
                return True
    return False


def run_rag_evaluation():
    dataset_path = os.path.join(PROJECT_ROOT, "evaluation", "dataset.json")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    logger.info("Initializing LangGraph RAGPipeline for full generation evaluation...")
    pipeline = RAGPipeline()

    total_queries = len(dataset)
    successful_answers = 0
    context_available_count = 0
    correct_source_attributed_count = 0
    latencies = []

    eval_results = []

    print("\n" + "=" * 75)
    print("END-TO-END RAG PIPELINE EVALUATION (16 QUESTIONS)")
    print("=" * 75)

    for idx, item in enumerate(dataset, start=1):
        q_id = item["id"]
        question = item["question"]
        expected_answer = item["expected_answer"]
        expected_sources = item["expected_sources"]

        t0 = time.perf_counter()
        state = pipeline.invoke(
            query=question,
            dense_top_k=10,
            sparse_top_k=10,
            final_top_k=3,
        )
        latency = time.perf_counter() - t0
        latencies.append(latency)

        answer = state.get("answer", "").strip()
        context = state.get("context", "").strip()
        sources = state.get("sources", [])
        error = state.get("error")

        has_answer = bool(answer and not error)
        has_context = bool(context and len(sources) > 0)
        has_correct_source = is_source_attributed(sources, expected_sources)

        if has_answer:
            successful_answers += 1
        if has_context:
            context_available_count += 1
        if has_correct_source:
            correct_source_attributed_count += 1

        exp_src_str = ", ".join([f"{s['source']} (p.{s['page']})" for s in expected_sources])
        act_src_str = ", ".join([f"{s['filename']} (p.{s['page']})" for s in sources])

        eval_results.append(
            {
                "id": q_id,
                "question": question,
                "answer": answer,
                "expected_answer": expected_answer,
                "sources": sources,
                "has_correct_source": has_correct_source,
                "latency": latency,
            }
        )

        print(f"\n[{idx}/{total_queries}] ID: {q_id} | Category: {item.get('category', '')}")
        print(f"QUESTION : {question}")
        print(f"ANSWER   : {answer}")
        print(f"EXPECTED : {expected_answer}")
        print(f"EXP. SRC : {exp_src_str}")
        print(f"ACT. SRC : {act_src_str}")
        print(f"SRC HIT  : {'YES' if has_correct_source else 'NO'} | LATENCY: {latency:.2f}s")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    success_rate = (successful_answers / total_queries) * 100.0
    context_rate = (context_available_count / total_queries) * 100.0
    source_rate = (correct_source_attributed_count / total_queries) * 100.0

    print("\n" + "=" * 75)
    print("RAG EVALUATION SUMMARY METRICS")
    print("=" * 75)
    print(f"Total Evaluation Questions     : {total_queries}")
    print(f"Successful Answers Generated   : {successful_answers}/{total_queries} ({success_rate:.1f}%)")
    print(f"Context Availability           : {context_available_count}/{total_queries} ({context_rate:.1f}%)")
    print(f"Correct Source Attribution     : {correct_source_attributed_count}/{total_queries} ({source_rate:.1f}%)")
    print()
    print("LATENCY BASELINE (END-TO-END):")
    print(f"  Average Total Latency: {avg_latency:.2f} seconds")
    print(f"  Minimum Total Latency: {min_latency:.2f} seconds")
    print(f"  Maximum Total Latency: {max_latency:.2f} seconds")
    print("=" * 75 + "\n")

    return {
        "total_queries": total_queries,
        "successful_answers": successful_answers,
        "context_rate": context_rate,
        "source_rate": source_rate,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
    }


if __name__ == "__main__":
    run_rag_evaluation()
