import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Union

import torch
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.logger import logger
from app.engine.retrieval.rank_fusion import FusedResult


@dataclass
class RerankedResult:
    """
    Unified representation of a retrieved document chunk after cross-encoder reranking.

    Attributes:
        chunk_id: Stable deterministic chunk identifier.
        document: The original LangChain Document preserving text and metadata.
        rerank_score: Cross-Encoder relevance score (higher means more relevant).
        rrf_score: Original Reciprocal Rank Fusion score before reranking.
        retrieval_sources: Retrieval systems that retrieved this candidate (e.g. ['faiss', 'bm25']).
    """

    chunk_id: str
    document: Document
    rerank_score: float
    rrf_score: float
    retrieval_sources: List[str] = field(default_factory=list)


class CrossEncoderReranker:
    """
    Precision Cross-Encoder reranker evaluating (query, document) pairs.

    Responsibilities:
    - Load a local CrossEncoder model once during initialization.
    - Accept query and candidate list from HybridRetriever (FusedResult).
    - Score all query-document pairs simultaneously using the cross-encoder.
    - Sort candidates by descending cross-encoder relevance score.
    - Preserve original RRF scores, chunk IDs, documents, and retrieval source tracking.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or getattr(
            settings, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(
            f"Loading CrossEncoder model '{self.model_name}' on device '{self.device}'..."
        )

        start_time = time.perf_counter()
        self.model = CrossEncoder(
            model_name=self.model_name,
            device=self.device,
        )
        self.load_time_seconds = time.perf_counter() - start_time

        logger.info(
            f"CrossEncoder model '{self.model_name}' loaded in {self.load_time_seconds:.2f} seconds."
        )

    def rerank(
        self,
        query: str,
        candidates: Sequence[Union[FusedResult, Document]],
        final_top_k: Optional[int] = None,
    ) -> List[RerankedResult]:
        """
        Rerank a list of candidate documents using cross-encoder relevance scoring.

        Args:
            query: User financial query string.
            candidates: Sequence of FusedResult items (from HybridRetriever) or Document items.
            final_top_k: Number of top reranked results to return (defaults to settings.FINAL_CONTEXT_K).

        Returns:
            List of RerankedResult sorted by descending rerank_score.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if not candidates:
            logger.info("Empty candidate list provided to reranker. Returning empty list.")
            return []

        top_k = final_top_k if final_top_k is not None else settings.FINAL_CONTEXT_K

        if top_k <= 0:
            raise ValueError(f"final_top_k must be greater than zero, got {top_k}.")

        # Normalize candidates into standard list
        parsed_candidates = []
        pairs = []

        for item in candidates:
            if isinstance(item, FusedResult):
                doc = item.document
                cid = item.chunk_id
                rrf = item.fused_score
                sources = item.retrieval_sources
            elif isinstance(item, Document):
                doc = item
                cid = doc.metadata.get("chunk_id", "")
                rrf = 0.0
                sources = ["direct"]
            else:
                raise TypeError(
                    f"Expected FusedResult or Document in candidates, got {type(item)}."
                )

            if not cid:
                raise ValueError("Candidate Document is missing 'chunk_id' in metadata.")

            parsed_candidates.append((cid, doc, rrf, sources))
            pairs.append([query, doc.page_content])

        logger.info(
            f"Reranking {len(pairs)} candidates for query {query!r} using {self.model_name}..."
        )

        start_time = time.perf_counter()
        scores = self.model.predict(pairs)
        rerank_latency = time.perf_counter() - start_time

        logger.info(
            f"Cross-encoder scoring completed in {rerank_latency:.4f} seconds."
        )

        # Build RerankedResult objects
        results = [
            RerankedResult(
                chunk_id=cid,
                document=doc,
                rerank_score=float(scores[idx]),
                rrf_score=rrf,
                retrieval_sources=sources,
            )
            for idx, (cid, doc, rrf, sources) in enumerate(parsed_candidates)
        ]

        # Sort descending by rerank_score
        results.sort(key=lambda r: r.rerank_score, reverse=True)

        effective_top_k = min(top_k, len(results))
        final_results = results[:effective_top_k]

        logger.info(
            f"Reranking complete. Returned top {len(final_results)} of {len(candidates)} candidates."
        )

        return final_results
