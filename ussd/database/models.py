"""
Database Models for USSD App
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from geoalchemy2 import Geometry
import uuid
from datetime import datetime

Base = declarative_base()


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
