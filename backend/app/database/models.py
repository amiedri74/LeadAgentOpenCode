import uuid
from datetime import datetime, timezone

_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(50), nullable=False)
    source_id = Column(String(255))
    company_name = Column(String(255))
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(512))
    address = Column(Text)
    city = Column(String(100))
    zip_code = Column(String(10))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    permit_number = Column(String(50))
    permit_type = Column(String(50))
    permit_subtype = Column(String(50))
    permit_status = Column(String(50))
    project_description = Column(Text)
    estimated_cost = Column(Numeric(12, 2))
    service_category = Column(String(50))
    urgency = Column(String(20))
    score = Column(Integer, default=0)
    is_high_value = Column(Boolean, default=False)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        Index("idx_leads_source", "source"),
        Index("idx_leads_service_category", "service_category"),
        Index("idx_leads_score", "score"),
        Index("idx_leads_zip_code", "zip_code"),
        Index("idx_leads_is_high_value", "is_high_value"),
        Index("idx_leads_source_source_id", "source", "source_id"),
    )
