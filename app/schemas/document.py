import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Metadata response schema for an uploaded financial document."""

    id: int = Field(..., description="Unique database ID of the document.")
    filename: str = Field(..., description="Sanitized stored filename.")
    original_filename: str = Field(..., description="Original user-uploaded filename.")
    file_size_bytes: int = Field(..., description="Size of the document in bytes.")
    page_count: int = Field(default=0, description="Total number of extracted pages.")
    chunk_count: int = Field(default=0, description="Total number of generated chunks.")
    processing_status: str = Field(..., description="Status: PENDING, PROCESSING, READY, or FAILED.")
    processing_error: Optional[str] = Field(default=None, description="Error message if processing failed.")
    created_at: datetime.datetime = Field(..., description="Timestamp of document upload.")
    updated_at: datetime.datetime = Field(..., description="Timestamp of last status update.")


class DocumentListResponse(BaseModel):
    """Response schema for listing registered financial documents."""

    total: int = Field(..., description="Total count of registered documents.")
    ready_count: int = Field(..., description="Count of documents ready for querying.")
    documents: List[DocumentResponse] = Field(default_factory=list, description="List of document metadata objects.")


class DocumentUploadResponse(BaseModel):
    """Response schema returned upon document upload."""

    message: str = Field(..., description="User-facing status message.")
    document: DocumentResponse = Field(..., description="Registered document record.")
