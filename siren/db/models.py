from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Text, Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(50), unique=True, nullable=False, index=True)
    severity = Column(String(5))
    affected_service = Column(String(100), index=True)
    affected_region = Column(String(50))
    alert_source = Column(String(50))
    incident_summary = Column(Text)
    root_cause = Column(Text)
    root_cause_confidence = Column(Float)
    workflow_status = Column(String(30), nullable=False)
    raw_alert = Column(JSON)
    similar_incidents_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True))
    qdrant_vector_id = Column(String(100))
    postmortem_id = Column(String(50))


class ActionAudit(Base):
    __tablename__ = "action_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(50), nullable=False, index=True)
    action_id = Column(String(50))
    tool_name = Column(String(100))
    tool_args = Column(JSON)
    classification = Column(String(20))  # READ | REVERSIBLE | DESTRUCTIVE
    approved = Column(Boolean)
    approved_by = Column(String(100))  # Slack user name
    executed_at = Column(DateTime(timezone=True))
    result_status = Column(String(20))  # success | error | blocked | rate_limited
    result_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
