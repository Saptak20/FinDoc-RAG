from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.engine.ingestion.ingest import ingest_document
from app.schemas.document import DocumentResponse
from app.core.logger import logger

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a financial document (PDF or TXT) to parse, chunk, embed, and index in pgvector.
    """
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Only PDF and TXT files are accepted."
        )
        
    try:
        content = await file.read()
        db_doc = await ingest_document(file.filename, content, db)
        return db_doc
    except Exception as e:
        logger.error(f"Failed to ingest document {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
