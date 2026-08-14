from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

from langchain_core.documents import Document

from app.core.logger import logger


@dataclass
class FusedResult:
    """
    Unified representation of a retrieved document after rank fusion.

    Attributes:
        chunk_id: Stable deterministic chunk identifier.
        document: The original LangChain Document preserving text and metadata.
        fused_score: Computed reciprocal rank fusion score.
        retrieval_sources: List of retrieval systems that retrieved this chunk (e.g. ['faiss', 'bm25']).
    """

    chunk_id: str
    document: Document
    fused_score: float
    retrieval_sources: List[str] = field(default_factory=list)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Tuple[str, Sequence[Union[Document, Tuple[Document, float]]]]],
    rrf_k: int = 60,
    top_k: Optional[int] = None,
) -> List[FusedResult]:
    """
    Combine multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    RRF formula for a document d across retrieval systems M:
        RRF(d) = sum_{m in M} (1 / (rrf_k + rank_m(d)))

    where rank_m(d) is 1-indexed (1, 2, 3, ...).

    Args:
        ranked_lists: A sequence of tuples in the form (source_name, ranked_results),
                      where ranked_results is an ordered sequence of Document objects
                      or (Document, score) tuples (rank 1 = index 0).
        rrf_k: Smoothing constant parameter (default: 60). Must be positive.
        top_k: Optional maximum number of fused results to return.

    Returns:
        List of FusedResult sorted by descending fused_score.
    """
    if rrf_k <= 0:
        raise ValueError(f"rrf_k must be a positive integer, got {rrf_k}.")

    if top_k is not None and top_k <= 0:
        raise ValueError(f"top_k must be greater than zero, got {top_k}.")

    accumulator: Dict[str, Dict] = {}

    for source_name, results in ranked_lists:
        if not results:
            continue

        for rank_idx, item in enumerate(results):
            rank = rank_idx + 1

            if isinstance(item, tuple):
                doc = item[0]
            elif isinstance(item, Document):
                doc = item
            else:
                raise TypeError(
                    f"Expected Document or (Document, score) tuple in ranked list from '{source_name}', got {type(item)}."
                )

            chunk_id = doc.metadata.get("chunk_id")
            if not chunk_id:
                raise ValueError(
                    f"Document at rank {rank} from source '{source_name}' is missing 'chunk_id' in metadata."
                )

            rrf_score = 1.0 / (rrf_k + rank)

            if chunk_id not in accumulator:
                accumulator[chunk_id] = {
                    "document": doc,
                    "fused_score": 0.0,
                    "sources": [],
                }

            accumulator[chunk_id]["fused_score"] += rrf_score

            if source_name not in accumulator[chunk_id]["sources"]:
                accumulator[chunk_id]["sources"].append(source_name)

    # Build FusedResult list
    fused_results = [
        FusedResult(
            chunk_id=cid,
            document=entry["document"],
            fused_score=entry["fused_score"],
            retrieval_sources=entry["sources"],
        )
        for cid, entry in accumulator.items()
    ]

    # Sort descending by fused_score
    fused_results.sort(key=lambda r: r.fused_score, reverse=True)

    if top_k is not None:
        fused_results = fused_results[:top_k]

    logger.info(
        f"Reciprocal Rank Fusion completed. "
        f"Input lists: {len(ranked_lists)}, "
        f"unique candidates: {len(accumulator)}, "
        f"returned: {len(fused_results)}"
    )

    return fused_results


class RankFusion:
    """
    Convenience wrapper for Reciprocal Rank Fusion of dense and sparse retrievers.
    """

    def __init__(self, rrf_k: int = 60):
        if rrf_k <= 0:
            raise ValueError(f"rrf_k must be positive, got {rrf_k}.")
        self.rrf_k = rrf_k

    def fuse(
        self,
        dense_results: Sequence[Union[Document, Tuple[Document, float]]],
        sparse_results: Sequence[Union[Document, Tuple[Document, float]]],
        dense_source_name: str = "faiss",
        sparse_source_name: str = "bm25",
        top_k: Optional[int] = None,
    ) -> List[FusedResult]:
        """
        Fuse dense and sparse retrieval results using RRF.
        """
        ranked_lists = [
            (dense_source_name, dense_results),
            (sparse_source_name, sparse_results),
        ]
        return reciprocal_rank_fusion(
            ranked_lists=ranked_lists,
            rrf_k=self.rrf_k,
            top_k=top_k,
        )
