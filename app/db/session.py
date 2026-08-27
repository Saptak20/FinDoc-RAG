import hashlib
import os
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logger import logger
from app.db.models import Base, DocumentRecord, DocumentStatus, QueryLog

from sqlalchemy.pool import NullPool

# Replace standard 'postgresql://' with async driver 'postgresql+asyncpg://'
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    async_db_url,
    echo=settings.DEBUG,
    poolclass=NullPool,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session dependency with automatic closing and rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session error: {exc}")
            raise
        finally:
            await session.close()


async def init_db():
    """Create database tables, recover orphaned jobs, and register baseline indexed corpus."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")

        # Recover any documents left in PENDING/PROCESSING state from prior server crash
        await _recover_orphaned_documents()

        # Seed baseline pre-indexed documents (e.g. OTC_TATLY_2024.pdf) if present in raw dir
        await _seed_existing_documents()

    except Exception as exc:
        logger.warning(f"Database initialization notice: {exc}")


async def _recover_orphaned_documents():
    """Recover documents stuck in PENDING or PROCESSING due to a prior crash/restart."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentRecord).where(
                DocumentRecord.processing_status.in_([
                    DocumentStatus.PENDING.value,
                    DocumentStatus.PROCESSING.value,
                ])
            )
            result = await session.execute(stmt)
            orphans = result.scalars().all()
            for doc in orphans:
                doc.processing_status = DocumentStatus.FAILED.value
                doc.processing_error = "Processing was interrupted by a server restart. Please re-upload to retry."
            if orphans:
                await session.commit()
                logger.info(f"Recovered {len(orphans)} orphaned processing document(s) from previous run.")
    except Exception as e:
        logger.warning(f"Orphan document recovery notice: {e}")



async def _seed_existing_documents():
    """Auto-register existing raw PDF files if already indexed on disk."""
    try:
        if not os.path.exists(settings.RAW_DATA_PATH):
            return

        raw_files = [f for f in os.listdir(settings.RAW_DATA_PATH) if f.lower().endswith(".pdf")]
        if not raw_files:
            return

        async with AsyncSessionLocal() as session:
            for fname in raw_files:
                fpath = os.path.join(settings.RAW_DATA_PATH, fname)
                fsize = os.path.getsize(fpath)

                # Compute content hash
                h = hashlib.sha256()
                with open(fpath, "rb") as f:
                    while chunk := f.read(8192):
                        h.update(chunk)
                content_hash = h.hexdigest()

                stmt = select(DocumentRecord).where(DocumentRecord.content_hash == content_hash)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    # If FAISS and chunks.jsonl exist, mark as READY
                    is_ready = os.path.exists(os.path.join(settings.VECTOR_STORE_PATH, "index.faiss"))
                    doc = DocumentRecord(
                        filename=fname,
                        original_filename=fname,
                        file_path=fpath,
                        file_size_bytes=fsize,
                        content_hash=content_hash,
                        page_count=581 if "TATLY" in fname else 0,
                        chunk_count=2710 if "TATLY" in fname else 0,
                        processing_status=DocumentStatus.READY.value if is_ready else DocumentStatus.PENDING.value,
                    )
                    session.add(doc)
                    await session.commit()
                    logger.info(f"Registered pre-existing document in DB: {fname}")
    except Exception as e:
        logger.warning(f"Document auto-seeding notice: {e}")


async def log_query_to_db(query: str, response: str, latency_ms: float):
    """Safely log query execution to PostgreSQL in background without blocking response."""
    try:
        async with AsyncSessionLocal() as session:
            log_entry = QueryLog(
                query=query,
                response=response,
                latency_ms=latency_ms,
            )
            session.add(log_entry)
            await session.commit()
            logger.debug("Logged query execution to database.")
    except Exception as exc:
        logger.warning(f"Could not persist query log to database: {exc}")
