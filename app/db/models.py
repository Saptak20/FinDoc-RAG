from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime
import datetime


Base = declarative_base()


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