import asyncio
import datetime
import os
import re
from typing import Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from sqlalchemy import select

from app.api.dependencies import get_rag_pipeline
from app.core.config import settings
from app.core.logger import logger
from app.db.models import DocumentRecord, DocumentStatus
from app.db.session import AsyncSessionLocal
from app.engine.ingestion.chunk_store import ChunkStore
from app.engine.ingestion.ingestor import SECIngestor


def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent path traversal or special character issues."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    if not clean.lower().endswith(".pdf"):
        clean += ".pdf"
    return clean


def validate_pdf_content(file_bytes: bytes, filename: str) -> None:
    """
    Validate uploaded file format, magic header, and size limits.
    """
    if not filename.lower().endswith(".pdf"):
        raise ValueError(f"Invalid file extension. Only .pdf files are supported, got '{filename}'.")

    if not file_bytes or len(file_bytes) < 5:
        raise ValueError("Uploaded file is empty or corrupted.")

    # Check PDF magic bytes '%PDF-'
    if not file_bytes.startswith(b"%PDF-"):
        raise ValueError("File header does not match a valid PDF specification (%PDF-).")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(
            f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB "
            f"({len(file_bytes) / (1024*1024):.1f}MB uploaded)."
        )


# Concurrency lock to serialize background indexing jobs and prevent disk corruption
_ingestion_lock = asyncio.Lock()


def _sync_process_document(file_path: str, filename: str) -> Tuple[int, int]:
    """
    Synchronous document extraction, chunking, embedding, and FAISS indexing pipeline.
    Runs inside a separate thread pool to ensure non-blocking event loop execution.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found at path: {file_path}")

    # 1. Extract text from PDF
    logger.info(f"Extracting pages from: {file_path}")
    loader = PyPDFLoader(file_path=file_path)
    pages = loader.load()

    if not pages:
        raise ValueError(f"No readable text pages found in PDF: {filename}")

    page_count = len(pages)
    logger.info(f"Extracted {page_count} pages from {filename}")

    # 2. Chunk documents
    ingestor = SECIngestor()
    chunks = ingestor.chunk_documents(pages)

    if not chunks:
        raise ValueError(f"Document chunking produced zero chunks for: {filename}")

    # 3. Assign deterministic chunk IDs
    chunks = ingestor.assign_chunk_ids(chunks)
    chunk_count = len(chunks)
    logger.info(f"Generated {chunk_count} chunks for {filename}")

    # 4. Update Canonical Chunk Store (chunks.jsonl)
    chunk_store = ChunkStore()
    existing_chunks = []
    if os.path.exists(chunk_store.file_path):
        try:
            all_prev_chunks = chunk_store.load_chunks()
            # Exclude any previous chunks from this same document filename for idempotency
            existing_chunks = [
                c for c in all_prev_chunks
                if os.path.basename(c.metadata.get("source", "")) != filename
            ]
        except Exception as e:
            logger.warning(f"Could not load previous chunks, will create fresh store: {e}")
            existing_chunks = []

    combined_chunks = existing_chunks + chunks

    # 5. Update FAISS Vector Store
    embeddings = OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

    faiss_index_path = os.path.join(settings.VECTOR_STORE_PATH, "index.faiss")
    if os.path.exists(faiss_index_path):
        logger.info("Loading existing FAISS vector store to add new document embeddings...")
        vector_store = FAISS.load_local(
            folder_path=settings.VECTOR_STORE_PATH,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )
        # Add new chunks incrementally in controlled batches of 32
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vector_store.add_documents(batch)
            logger.info(f"Embedded and added batch {i // batch_size + 1} ({len(batch)} chunks) to FAISS.")

        vector_store.save_local(settings.VECTOR_STORE_PATH)
        logger.info(f"Saved updated FAISS store. Total vectors: {vector_store.index.ntotal}")
    else:
        logger.info("Building initial FAISS vector store...")
        vector_store = ingestor.build_vector_store(chunks=combined_chunks, batch_size=32)

    # Save chunks only after embedding has succeeded without error
    chunk_store.save_chunks(combined_chunks)
    logger.info(f"Updated canonical chunk corpus with total {len(combined_chunks)} chunks.")

    # 6. Hot-reload active RAG pipeline retrievers
    try:
        pipeline = get_rag_pipeline()
        pipeline.reload_retrievers()
        logger.info("Hot-reloaded active RAGPipeline retrievers successfully.")
    except Exception as e:
        logger.warning(f"Pipeline hot-reload notification: {e}")

    return (page_count, chunk_count)


async def process_document_pipeline(document_id: int) -> Tuple[int, int]:
    """
    Background worker that extracts, chunks, embeds, and indexes a registered PDF document.
    Serialized via _ingestion_lock to guarantee thread/process safety against concurrent disk mutations.
    """
    async with _ingestion_lock:
        logger.info(f"Starting background ingestion for Document ID: {document_id}")

        # 1. Fetch document record from database
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
            res = await session.execute(stmt)
            doc_record = res.scalar_one_or_none()

            if not doc_record:
                logger.error(f"Document record ID {document_id} not found in database.")
                return (0, 0)

            # Check if document was deleted while waiting in queue
            if not os.path.exists(doc_record.file_path):
                logger.warning(f"Document {doc_record.filename} file path does not exist. Marking as FAILED.")
                doc_record.processing_status = DocumentStatus.FAILED.value
                doc_record.processing_error = "Source file was removed before processing could begin."
                await session.commit()
                return (0, 0)

            doc_record.processing_status = DocumentStatus.PROCESSING.value
            doc_record.processing_error = None
            await session.commit()

            file_path = doc_record.file_path
            filename = doc_record.filename

        try:
            # Offload sync CPU/IO ingestion to background thread
            page_count, chunk_count = await asyncio.to_thread(_sync_process_document, file_path, filename)

            # 2. Mark document as READY in DB
            async with AsyncSessionLocal() as session:
                stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
                res = await session.execute(stmt)
                record = res.scalar_one()
                record.page_count = page_count
                record.chunk_count = chunk_count
                record.processing_status = DocumentStatus.READY.value
                record.processing_error = None
                record.updated_at = datetime.datetime.utcnow()
                await session.commit()

            logger.info(f"Document ID {document_id} ({filename}) successfully ingested and READY for querying.")
            return (page_count, chunk_count)

        except Exception as exc:
            logger.exception(f"Document processing failed for ID {document_id}: {exc}")
            # Sanitize error for internal record
            sanitized_err = str(exc).split("\n")[0]
            async with AsyncSessionLocal() as session:
                stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
                res = await session.execute(stmt)
                record = res.scalar_one_or_none()
                if record:
                    record.processing_status = DocumentStatus.FAILED.value
                    record.processing_error = f"Ingestion error: {sanitized_err}"
                    record.updated_at = datetime.datetime.utcnow()
                    await session.commit()
            return (0, 0)


