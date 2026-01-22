import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.db.interfaces.postgresql import Base


class Paper(Base):
    __tablename__ = "papers"
    # primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # core metadata
    arxiv_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(Text, nullable=False)
    categories = Column(JSON, nullable=False)
    pdf_url = Column(String, nullable=False)

    # parsing metadata
    pdf_processed = Column(Boolean, nullable=False, default=False)
    parser_used = Column(String, nullable=True)

    # parsed PDF content
    raw_text = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)

    # timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
