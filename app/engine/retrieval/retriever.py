import os
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

from app.core.config import settings
from app.core.logger import logger


class DenseRetriever:
    """
    Dense semantic retriever backed by a persisted FAISS vector store.

    Responsibilities:
    - Initialize the same embedding model used during ingestion.
    - Load the persisted FAISS index from disk.
    - Validate that the loaded index is not empty.
    - Execute semantic similarity search.
    - Return retrieved documents with FAISS distance scores.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
    ):
        self.persist_dir = (
            persist_dir or settings.VECTOR_STORE_PATH
        )

        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

        self.vector_store = self._load_vector_store()

    def _load_vector_store(self) -> FAISS:
        """
        Load the persisted FAISS vector store from disk.
        """

        logger.info(
            f"Loading FAISS vector store from: {self.persist_dir}"
        )

        index_path = os.path.join(
            self.persist_dir,
            "index.faiss",
        )

        metadata_path = os.path.join(
            self.persist_dir,
            "index.pkl",
        )

        if not os.path.exists(index_path):
            raise FileNotFoundError(
                f"FAISS index file not found: {index_path}"
            )

        if not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"FAISS metadata file not found: {metadata_path}"
            )

        vector_store = FAISS.load_local(
            folder_path=self.persist_dir,
            embeddings=self.embeddings,
            allow_dangerous_deserialization=True,
        )

        vector_count = vector_store.index.ntotal

        if vector_count <= 0:
            raise ValueError(
                "Loaded FAISS vector store is empty."
            )

        logger.info(
            f"FAISS vector store loaded successfully. "
            f"Total vectors: {vector_count}"
        )

        return vector_store

    def dense_search(
        self,
        query: str,
        k: int | None = None,
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve semantically similar documents from FAISS.

        Returns:
            List of tuples:

            [
                (Document, distance_score),
                (Document, distance_score),
                ...
            ]

        Important:
            For the default FAISS distance strategy used here,
            lower scores indicate closer matches.
        """

        if not query or not query.strip():
            raise ValueError(
                "Search query cannot be empty."
            )

        top_k = k if k is not None else settings.TOP_K

        if top_k <= 0:
            raise ValueError(
                "k must be greater than zero."
            )

        logger.info(
            f"Running dense retrieval. "
            f"Query: {query!r}, "
            f"top_k: {top_k}"
        )

        results = (
            self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
            )
        )

        logger.info(
            f"Dense retrieval completed. "
            f"Results returned: {len(results)}"
        )

        return results

    @property
    def vector_count(self) -> int:
        """
        Return the number of vectors currently stored in FAISS.
        """

        return self.vector_store.index.ntotal