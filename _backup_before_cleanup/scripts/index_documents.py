import asyncio
import os
from app.db.session import AsyncSessionLocal
from app.engine.ingestion.ingest import ingest_document
from app.core.logger import logger
from app.db.models import Base
from app.db.session import engine
from sqlalchemy import text

DATA_DIR = "data"

async def index_all_documents():
    """
    Scans the data directory, and processes any PDF or TXT documents found,
    generating embeddings using local Ollama.
    """
    # Initialize DB schema if not already initialized
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)

    if not os.path.exists(DATA_DIR):
        logger.warning(f"Data directory '{DATA_DIR}' does not exist. Creating it.")
        os.makedirs(DATA_DIR)
        return

    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.pdf', '.txt'))]
    if not files:
        logger.info(f"No PDF or TXT files found in '{DATA_DIR}' directory.")
        return

    logger.info(f"Found {len(files)} file(s) to index.")
    
    async with AsyncSessionLocal() as db:
        for filename in files:
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                
                logger.info(f"Indexing {filename}...")
                await ingest_document(filename, file_bytes, db)
                logger.info(f"Finished indexing {filename}.")
            except Exception as e:
                logger.error(f"Error indexing {filename}: {e}")

if __name__ == "__main__":
    asyncio.run(index_all_documents())
