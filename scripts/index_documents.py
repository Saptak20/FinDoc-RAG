import os
import sys
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger
from app.engine.ingestion.ingestor import SECIngestor
from app.engine.ingestion.chunk_store import ChunkStore


def main():
    """Run the complete document ingestion pipeline."""

    logger.info(
        "Starting FinDoc-RAG document ingestion process."
    )

    start_time = time.perf_counter()

    try:
        ingestor = SECIngestor()
        chunk_store = ChunkStore()

        # Step 1: Load PDF pages.
        documents = ingestor.load_documents()

        # Step 2: Split pages into overlapping chunks.
        chunks = ingestor.chunk_documents(documents)

        # Step 3: Assign stable identity metadata.
        chunks = ingestor.assign_chunk_ids(chunks)

        # Step 4: Persist the canonical chunk corpus for BM25.
        chunk_store.save_chunks(chunks)

        # Step 5: Embed the same chunks and build FAISS.
        vector_store = ingestor.build_vector_store(
            chunks=chunks,
            batch_size=32,
        )

        elapsed_time = time.perf_counter() - start_time

        logger.info(
            f"Ingestion completed successfully. "
            f"Pages loaded: {len(documents)}, "
            f"chunks persisted: {len(chunks)}, "
            f"vectors stored: {vector_store.index.ntotal}, "
            f"elapsed time: {elapsed_time:.2f} seconds."
        )

    except Exception:
        logger.exception(
            "Document ingestion process failed."
        )
        raise


if __name__ == "__main__":
    main()