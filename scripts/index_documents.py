import os
import sys
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__),"..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.core.logger import logger 
from app.engine.ingestion.ingestor import SECIngestor

def main():
    """Run the complete document ingestion pipeline."""
    logger.info("Starting FinDoc-RAG document ingestion process.")
    start_time = time.perf_counter()

    try:
        ingestor = SECIngestor()
        documents = ingestor.load_documents()
        chunks = ingestor.chunk_documents(documents)
        vector_store = ingestor.build_vector_store(chunks)
        elapsed_time = time.perf_counter() - start_time

        logger.info(
            f"Ingestion completed successfully"
            f"Pages loaded: {len(documents)},"
            f"chunks indexed: {len(chunks)},"
            f"vectors stored: {vector_store.index.ntotal},"
            f"elapsed time: {elapsed_time:2f} seconds."
        )
    except Exception:
        logger.exception("Document ingestion process failed.")
        raise    

if __name__ == "__main__":
    main()    