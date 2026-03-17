"""
SQLAlchemy models for Unified Wildlife Reporting App
"""
from sqlalchemy import (
    Column, String, Boolean, Float, DateTime, Text, Index, JSON,
    func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base
from geoalchemy2 import Geometry
from datetime import datetime
import uuid

Base = declarative_base()


# =============================================================================
# USSD Models
# =============================================================================

class USSDReport(Base):
    """USSD incident reports - all types in one table"""
    __tablename__ = "ussd_reports"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(20), unique=True, nullable=False, index=True)

    # Classification
    report_type = Column(String(30), nullable=False, index=True)
    incident_type = Column(String(50), index=True)

    # Reporter
    phone_number = Column(String(20), nullable=False, index=True)

    # Animal
    species = Column(String(50), nullable=False)
    species_is_other = Column(Boolean, default=False)
    animal_count = Column(String(20))

    # Location
    location_name = Column(String(100), nullable=False)
    location_is_other = Column(Boolean, default=False)
    location = Column(Geometry('POINT', srid=4326), nullable=True)

    # Severity & Priority
    severity = Column(String(20))
    priority = Column(String(20), nullable=False, index=True)

    # Environmental Context
    weather = Column(String(20))
    time_of_day = Column(String(20))

    # Type-specific data
    details = Column(JSON, default=dict)

    # Status
    status = Column(String(30), default='pending', index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    reported_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Assignment
    assigned_to = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Session
    session_id = Column(String(50), nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "incident_id": self.incident_id,
            "report_type": self.report_type,
            "incident_type": self.incident_type,
            "phone_number": self.phone_number,
            "species": self.species,
            "species_is_other": self.species_is_other,
            "animal_count": self.animal_count,
            "location_name": self.location_name,
            "location_is_other": self.location_is_other,
            "severity": self.severity,
            "priority": self.priority,
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "details": self.details,
            "status": self.status,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# SMS Models
# =============================================================================


class SMSReport(Base):
    """SMS-based incident reports"""
    __tablename__ = "sms_reports"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(20), unique=True, nullable=False)  # SMS-0001 format

    # Reporter info
    phone_number = Column(String(20), nullable=False, index=True)

    # Extracted data with confidence scores
    species = Column(String(50))
    species_confidence = Column(Float)
    incident_type = Column(String(50))
    incident_type_confidence = Column(Float)
    location_name = Column(String(100))
    location_confidence = Column(Float)
    animal_count = Column(String(20))
    severity = Column(String(20))

    # Raw data
    original_message = Column(Text, nullable=False)
    extracted_data = Column(JSONB)

    # Status & flags
    status = Column(String(30), default="pending")
    priority = Column(String(20), default="medium")
    needs_review = Column(Boolean, default=False)
    review_reason = Column(String(100))

    # Processing info
    extraction_method = Column(String(20))  # 'rule_based' or 'llm'
    overall_confidence = Column(Float)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Response tracking
    confirmation_sent = Column(Boolean, default=False)
    rangers_alerted = Column(Boolean, default=False)

    # Indexes
    __table_args__ = (
        Index('idx_sms_reports_status_priority', 'status', 'priority'),
        Index('idx_sms_reports_needs_review', 'needs_review',
              postgresql_where=(needs_review == True)),
    )

    def __repr__(self):
        return f"<SMSReport {self.incident_id}: {self.incident_type} at {self.location_name}>"


class SMSConversation(Base):
    """Track multi-turn SMS conversations for clarification"""
    __tablename__ = "sms_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), nullable=False, index=True)

    # Session state
    session_state = Column(String(50), default="new")
    # States: new, awaiting_species, awaiting_incident_type, awaiting_location, awaiting_confirmation

    # Partial extraction data
    partial_data = Column(JSONB)

    # Original message that started the conversation
    original_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime)

    def __repr__(self):
        return f"<SMSConversation {self.phone_number}: {self.session_state}>"


class SMSMessage(Base):
    """Log of all SMS messages (incoming and outgoing)"""
    __tablename__ = "sms_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(100), unique=True)  # Africa's Talking message ID

    # Direction
    direction = Column(String(10), nullable=False)  # 'incoming' or 'outgoing'

    # Message details
    phone_number = Column(String(20), nullable=False, index=True)
    message_text = Column(Text, nullable=False)

    # For incoming: extraction results
    extracted_data = Column(JSONB)

    # Link to report if created
    linked_report_id = Column(UUID(as_uuid=True))

    # Delivery status (for outgoing)
    status = Column(String(30))  # sent, delivered, failed

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_sms_messages_direction', 'direction'),
    )

    def __repr__(self):
        return f"<SMSMessage {self.direction}: {self.phone_number}>"
