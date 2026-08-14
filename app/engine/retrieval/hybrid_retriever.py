import os
from typing import List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.engine.retrieval.bm25_retriever import BM25Retriever
from app.engine.retrieval.rank_fusion import FusedResult, RankFusion
from app.engine.retrieval.retriever import DenseRetriever


class HybridRetriever:
    """
    Hybrid retriever combining dense semantic search (FAISS) and sparse lexical search (BM25)
    using Reciprocal Rank Fusion (RRF).

    Responsibilities:
    - Coordinate dense FAISS retrieval and sparse BM25 retrieval over the canonical corpus.
    - Perform Reciprocal Rank Fusion on both ranked result candidate lists.
    - Output a unified, deduplicated list of FusedResult items ordered by fused score.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        rank_fusion: Optional[RankFusion] = None,
        rrf_k: int = 60,
    ):
        self.persist_dir = persist_dir or settings.VECTOR_STORE_PATH

        logger.info("Initializing HybridRetriever...")

        try:
            self.dense_retriever = dense_retriever or DenseRetriever(
                persist_dir=self.persist_dir
            )
        except Exception as e:
            logger.error(f"Failed to initialize DenseRetriever: {e}")
            raise

        try:
            self.bm25_retriever = bm25_retriever or BM25Retriever(
                persist_dir=self.persist_dir
            )
        except Exception as e:
            logger.error(f"Failed to initialize BM25Retriever: {e}")
            raise

        self.rank_fusion = rank_fusion or RankFusion(rrf_k=rrf_k)

        logger.info(
            f"HybridRetriever initialized successfully. "
            f"FAISS vectors: {self.dense_retriever.vector_count}, "
            f"BM25 chunks: {self.bm25_retriever.chunk_count}, "
            f"RRF k: {self.rank_fusion.rrf_k}"
        )

    def hybrid_search(
        self,
        query: str,
        dense_top_k: Optional[int] = None,
        sparse_top_k: Optional[int] = None,
        final_top_k: Optional[int] = None,
    ) -> List[FusedResult]:
        """
        Execute hybrid retrieval across dense and sparse retrievers, fused with RRF.

        Args:
            query: User financial search query string.
            dense_top_k: Number of semantic candidates to retrieve from FAISS (defaults to settings.TOP_K).
            sparse_top_k: Number of lexical candidates to retrieve from BM25 (defaults to settings.TOP_K).
            final_top_k: Number of top fused candidates to return (defaults to settings.TOP_K).

        Returns:
            List of FusedResult sorted in descending order of fused_score.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        d_k = dense_top_k if dense_top_k is not None else settings.TOP_K
        s_k = sparse_top_k if sparse_top_k is not None else settings.TOP_K
        f_k = final_top_k if final_top_k is not None else settings.TOP_K

        if d_k <= 0:
            raise ValueError(f"dense_top_k must be greater than zero, got {d_k}.")
        if s_k <= 0:
            raise ValueError(f"sparse_top_k must be greater than zero, got {s_k}.")
        if f_k <= 0:
            raise ValueError(f"final_top_k must be greater than zero, got {f_k}.")

        logger.info(
            f"Executing hybrid search. Query: {query!r} | "
            f"dense_k: {d_k}, sparse_k: {s_k}, final_k: {f_k}"
        )

        # 1. Execute dense semantic retrieval
        dense_results = self.dense_retriever.dense_search(query=query, k=d_k)

        # 2. Execute sparse lexical retrieval
        sparse_results = self.bm25_retriever.bm25_search(query=query, k=s_k)

        # 3. Fuse ranked results with RRF
        fused_results = self.rank_fusion.fuse(
            dense_results=dense_results,
            sparse_results=sparse_results,
            dense_source_name="faiss",
            sparse_source_name="bm25",
            top_k=f_k,
        )

        logger.info(
            f"Hybrid search completed. "
            f"Dense candidates: {len(dense_results)}, "
            f"Sparse candidates: {len(sparse_results)}, "
            f"Fused results returned: {len(fused_results)}"
        )

        return fused_results

    def search(
        self,
        query: str,
        dense_top_k: Optional[int] = None,
        sparse_top_k: Optional[int] = None,
        final_top_k: Optional[int] = None,
    ) -> List[FusedResult]:
        """Alias for hybrid_search."""
        return self.hybrid_search(
            query=query,
            dense_top_k=dense_top_k,
            sparse_top_k=sparse_top_k,
            final_top_k=final_top_k,
        )

    @property
    def vector_count(self) -> int:
        """Total vectors in the dense store."""
        return self.dense_retriever.vector_count

    @property
    def chunk_count(self) -> int:
        """Total chunks in the sparse store."""
        return self.bm25_retriever.chunk_count
