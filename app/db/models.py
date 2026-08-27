import datetime
import enum
from sqlalchemy import Column, DateTime, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class QueryLog(Base):
    """
    Stores user queries, generated responses,
    and total request latency for analytics and debugging.
    """

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False)
    response = Column(String, nullable=False)
    latency_ms = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
    )


class DocumentRecord(Base):
    """
    Stores registry of uploaded financial documents,
    extraction stats, page/chunk metrics, and ingestion status.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    processing_status = Column(String(32), default=DocumentStatus.PENDING.value, index=True)
    processing_error = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )