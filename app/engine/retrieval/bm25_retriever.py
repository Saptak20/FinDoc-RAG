import os
import re
from typing import List, Tuple, Callable

import numpy as np
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.logger import logger
from app.engine.ingestion.chunk_store import ChunkStore


def default_tokenizer(text: str) -> List[str]:
    """
    Deterministic tokenizer suitable for financial documents.
    Lowercases text and extracts alphanumeric sequences and hyphenated words.
    """
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b", text.lower())


class BM25Retriever:
    """
    Sparse lexical retriever backed by BM25Okapi over the canonical chunk corpus.

    Responsibilities:
    - Load canonical document chunks from ChunkStore (chunks.jsonl).
    - Tokenize chunk contents using a deterministic financial-aware tokenizer.
    - Build an in-memory BM25 index.
    - Execute BM25 lexical search for user queries.
    - Return retrieved documents with BM25 relevance scores.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        filename: str = "chunks.jsonl",
        tokenizer: Callable[[str], List[str]] | None = None,
    ):
        self.persist_dir = persist_dir or settings.VECTOR_STORE_PATH
        self.filename = filename
        self.tokenizer = tokenizer or default_tokenizer

        self.chunk_store = ChunkStore(
            persist_dir=self.persist_dir,
            filename=self.filename,
        )

        self.chunks: List[Document] = []
        self.bm25_index: BM25Okapi | None = None

        self._load_and_index()

    def _load_and_index(self) -> None:
        """
        Load the canonical chunk corpus from disk and build the BM25 index.
        """
        logger.info(
            f"Loading canonical chunks for BM25 from: {self.chunk_store.file_path}"
        )
        self.chunks = self.chunk_store.load_chunks()

        if not self.chunks:
            raise ValueError("Loaded chunk corpus is empty for BM25 indexing.")

        logger.info(
            f"Tokenizing {len(self.chunks)} chunks for BM25 indexing."
        )
        tokenized_corpus = [
            self.tokenizer(doc.page_content)
            for doc in self.chunks
        ]

        logger.info("Building BM25Okapi index in memory.")
        self.bm25_index = BM25Okapi(tokenized_corpus)
        logger.info(
            f"BM25 index built successfully with {len(self.chunks)} document chunks."
        )

    def bm25_search(
        self,
        query: str,
        k: int | None = None,
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve lexically relevant documents from the canonical corpus using BM25.

        Returns:
            List of tuples:
            [
                (Document, bm25_score),
                (Document, bm25_score),
                ...
            ]

        Important:
            Higher BM25 scores indicate closer lexical matches.
            Results are sorted in descending order of BM25 score.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        top_k = k if k is not None else settings.TOP_K

        if top_k <= 0:
            raise ValueError("k must be greater than zero.")

        query_tokens = self.tokenizer(query)
        if not query_tokens:
            logger.warning(
                f"Query {query!r} yielded no valid tokens after tokenization."
            )
            return []

        logger.info(
            f"Running BM25 retrieval. "
            f"Query: {query!r}, "
            f"tokens: {query_tokens}, "
            f"top_k: {top_k}"
        )

        scores = self.bm25_index.get_scores(query_tokens)

        # Limit top_k to available documents
        effective_k = min(top_k, len(self.chunks))

        # Sort indices by score descending
        top_indices = np.argsort(scores)[::-1][:effective_k]

        results = [
            (self.chunks[idx], float(scores[idx]))
            for idx in top_indices
        ]

        logger.info(
            f"BM25 retrieval completed. "
            f"Results returned: {len(results)}"
        )

        return results

    def search(
        self,
        query: str,
        k: int | None = None,
    ) -> List[Tuple[Document, float]]:
        """Alias for bm25_search."""
        return self.bm25_search(query=query, k=k)

    @property
    def chunk_count(self) -> int:
        """
        Return the number of chunks currently indexed in the BM25 retriever.
        """
        return len(self.chunks)
