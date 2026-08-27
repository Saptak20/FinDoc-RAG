import hashlib
import os
import re
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_rag_pipeline
from app.core.config import settings
from app.core.logger import logger
from app.core.rate_limiter import rate_limit_delete, rate_limit_upload
from app.db.models import DocumentRecord, DocumentStatus
from app.db.session import get_db_session
from app.engine.ingestion.chunk_store import ChunkStore
from app.engine.ingestion.indexing_service import (
    process_document_pipeline,
    sanitize_filename,
    validate_pdf_content,
)
from app.engine.ingestion.ingestor import SECIngestor
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_upload)],
    summary="Upload and asynchronously ingest a financial PDF document",
)
@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_upload)],
    include_in_schema=False,
)
async def upload_document(

    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Financial PDF report or filing"),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """
    Validate, store, and trigger background ingestion for an uploaded financial PDF.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided with uploaded file.",
        )

    # 1. Read file bytes
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error(f"Error reading upload file stream: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content.",
        )

    # 2. Validate PDF format and size
    try:
        validate_pdf_content(file_bytes, file.filename)
    except ValueError as val_err:
        logger.warning(f"Upload validation failed for '{file.filename}': {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    # 3. Check for duplicates via content hash
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    stmt = select(DocumentRecord).where(DocumentRecord.content_hash == content_hash)
    result = await db.execute(stmt)
    existing_doc = result.scalar_one_or_none()

    if existing_doc:
        if existing_doc.processing_status == DocumentStatus.READY.value:
            logger.info(f"Duplicate document upload detected: {existing_doc.filename} is already READY.")
            return DocumentUploadResponse(
                message=f"Document '{existing_doc.original_filename}' is already indexed and available for querying.",
                document=DocumentResponse(
                    id=existing_doc.id,
                    filename=existing_doc.filename,
                    original_filename=existing_doc.original_filename,
                    file_size_bytes=existing_doc.file_size_bytes,
                    page_count=existing_doc.page_count,
                    chunk_count=existing_doc.chunk_count,
                    processing_status=existing_doc.processing_status,
                    processing_error=existing_doc.processing_error,
                    created_at=existing_doc.created_at,
                    updated_at=existing_doc.updated_at,
                ),
            )
        elif existing_doc.processing_status == DocumentStatus.PROCESSING.value:
            return DocumentUploadResponse(
                message=f"Document '{existing_doc.original_filename}' is currently being processed.",
                document=DocumentResponse(
                    id=existing_doc.id,
                    filename=existing_doc.filename,
                    original_filename=existing_doc.original_filename,
                    file_size_bytes=existing_doc.file_size_bytes,
                    page_count=existing_doc.page_count,
                    chunk_count=existing_doc.chunk_count,
                    processing_status=existing_doc.processing_status,
                    processing_error=existing_doc.processing_error,
                    created_at=existing_doc.created_at,
                    updated_at=existing_doc.updated_at,
                ),
            )

    # 4. Save file to disk
    safe_name = sanitize_filename(file.filename)
    os.makedirs(settings.RAW_DATA_PATH, exist_ok=True)
    destination_path = os.path.join(settings.RAW_DATA_PATH, safe_name)

    # If file with same name exists, add a short hash prefix to prevent overwriting different files
    if os.path.exists(destination_path) and (not existing_doc or existing_doc.filename != safe_name):
        safe_name = f"{content_hash[:8]}_{safe_name}"
        destination_path = os.path.join(settings.RAW_DATA_PATH, safe_name)

    with open(destination_path, "wb") as f:
        f.write(file_bytes)

    # 5. Create or reset database record
    if existing_doc:
        doc_record = existing_doc
        doc_record.file_path = destination_path
        doc_record.processing_status = DocumentStatus.PENDING.value
        doc_record.processing_error = None
    else:
        doc_record = DocumentRecord(
            filename=safe_name,
            original_filename=file.filename,
            file_path=destination_path,
            file_size_bytes=len(file_bytes),
            content_hash=content_hash,
            processing_status=DocumentStatus.PENDING.value,
        )
        db.add(doc_record)

    await db.commit()
    await db.refresh(doc_record)

    # 6. Dispatch background ingestion worker
    background_tasks.add_task(process_document_pipeline, doc_record.id)
    logger.info(f"Registered document ID {doc_record.id} ('{safe_name}') and scheduled background processing.")

    return DocumentUploadResponse(
        message=f"Document '{file.filename}' uploaded successfully. Background ingestion initiated.",
        document=DocumentResponse(
            id=doc_record.id,
            filename=doc_record.filename,
            original_filename=doc_record.original_filename,
            file_size_bytes=doc_record.file_size_bytes,
            page_count=doc_record.page_count,
            chunk_count=doc_record.chunk_count,
            processing_status=doc_record.processing_status,
            processing_error=doc_record.processing_error,
            created_at=doc_record.created_at,
            updated_at=doc_record.updated_at,
        ),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all registered financial documents and their indexing status",
)
async def list_documents(
    db: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """
    Retrieve all registered financial documents in the knowledge registry.
    """
    stmt = select(DocumentRecord).order_by(DocumentRecord.created_at.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()

    documents = [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            processing_status=doc.processing_status,
            processing_error=doc.processing_error,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in records
    ]

    ready_count = sum(1 for d in documents if d.processing_status == DocumentStatus.READY.value)

    return DocumentListResponse(
        total=len(documents),
        ready_count=ready_count,
        documents=documents,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get status and details for a specific document",
)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """
    Retrieve status and metadata for a single document by ID.
    """
    stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size_bytes=doc.file_size_bytes,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        processing_status=doc.processing_status,
        processing_error=doc.processing_error,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_delete)],
    summary="Delete a document and rebuild retrieval indexes",
)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a document, purge its chunks from the canonical corpus, rebuild indexes, and hot-reload retrievers.
    """
    stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    if doc.processing_status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{doc.original_filename}' is currently being indexed. Please wait until processing completes before deleting.",
        )


    filename = doc.filename
    file_path = doc.file_path

    # Delete raw file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted physical file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not remove physical file {file_path}: {e}")

    # Remove from database
    await db.delete(doc)
    await db.commit()

    # Clean from canonical chunk store and rebuild indexes if chunks exist
    chunk_store = ChunkStore()
    if os.path.exists(chunk_store.file_path):
        try:
            all_chunks = chunk_store.load_chunks()
            remaining_chunks = [
                c for c in all_chunks
                if os.path.basename(c.metadata.get("source", "")) != filename
            ]
            if remaining_chunks:
                chunk_store.save_chunks(remaining_chunks)
                ingestor = SECIngestor()
                ingestor.build_vector_store(chunks=remaining_chunks, batch_size=32)
                get_rag_pipeline().reload_retrievers()
                logger.info(f"Rebuilt indexes with {len(remaining_chunks)} remaining chunks after deleting {filename}.")
        except Exception as e:
            logger.error(f"Error rebuilding indexes after document deletion: {e}")

    return {
        "message": f"Document '{doc.original_filename}' deleted successfully.",
        "id": document_id,
    }
