"""
Database repository for Unified Wildlife Reporting App
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from geoalchemy2.functions import ST_MakePoint
import uuid
import logging

from database.models import USSDReport, SMSReport, SMSConversation, SMSMessage
from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# USSD Repository
# =============================================================================

class USSDReportRepository:
    """Repository for USSD Report operations"""

    def __init__(self, db: Session):
        self.db = db

    def generate_incident_id(self, report_type: str) -> str:
        """Generate next incident ID"""
        prefix = "INC" if report_type in ['emergency', 'past_incident'] else "SIG"

        last_report = self.db.query(USSDReport).filter(
            USSDReport.incident_id.like(f"{prefix}-%")
        ).order_by(desc(USSDReport.created_at)).first()

        if last_report and last_report.incident_id:
            try:
                last_num = int(last_report.incident_id.split("-")[1])
                return f"{prefix}-{str(last_num + 1).zfill(4)}"
            except (IndexError, ValueError):
                pass

        return f"{prefix}-0001"

    def create(self, data: Dict[str, Any]) -> USSDReport:
        """Create a new USSD report"""
        report = USSDReport(
            incident_id=data.get("incident_id") or self.generate_incident_id(data.get("report_type", "emergency")),
            report_type=data.get("report_type"),
            incident_type=data.get("incident_type"),
            phone_number=data.get("phone_number"),
            species=data.get("species"),
            species_is_other=data.get("species_is_other", False),
            animal_count=data.get("animal_count"),
            location_name=data.get("location_name"),
            location_is_other=data.get("location_is_other", False),
            severity=data.get("severity"),
            priority=data.get("priority"),
            weather=data.get("weather"),
            time_of_day=data.get("time_of_day"),
            details=data.get("details", {}),
            status=data.get("status", "pending"),
            session_id=data.get("session_id"),
        )

        if data.get("reported_at"):
            if isinstance(data["reported_at"], str):
                report.reported_at = datetime.fromisoformat(data["reported_at"])
            else:
                report.reported_at = data["reported_at"]

        if data.get("occurred_at"):
            if isinstance(data["occurred_at"], str):
                report.occurred_at = datetime.fromisoformat(data["occurred_at"])
            else:
                report.occurred_at = data["occurred_at"]

        location_coords = data.get("location_coords")
        if location_coords and location_coords.get("latitude") and location_coords.get("longitude"):
            report.location = ST_MakePoint(
                location_coords["longitude"],
                location_coords["latitude"]
            )

        self.db.add(report)
        self.db.flush()
        logger.info(f"Created USSD report: {report.incident_id}")
        return report

    def get_by_id(self, incident_id: str) -> Optional[USSDReport]:
        """Get report by incident ID"""
        return self.db.query(USSDReport).filter(
            USSDReport.incident_id == incident_id
        ).first()

    def get_reports(
        self,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[USSDReport]:
        """Get reports with optional filters"""
        query = self.db.query(USSDReport)

        if report_type:
            query = query.filter(USSDReport.report_type == report_type)
        if status:
            query = query.filter(USSDReport.status == status)
        if priority:
            query = query.filter(USSDReport.priority == priority)

        return query.order_by(desc(USSDReport.reported_at)).limit(limit).offset(offset).all()

    def get_pending_high_priority(self) -> List[USSDReport]:
        """Get pending high/critical priority reports"""
        return self.db.query(USSDReport).filter(
            USSDReport.status == "pending",
            USSDReport.priority.in_(["high", "critical"])
        ).order_by(desc(USSDReport.reported_at)).all()

    def update_status(
        self,
        incident_id: str,
        status: str,
        assigned_to: Optional[str] = None
    ) -> Optional[USSDReport]:
        """Update report status"""
        report = self.get_by_id(incident_id)
        if not report:
            return None

        report.status = status
        if assigned_to:
            report.assigned_to = assigned_to
            report.assigned_at = datetime.utcnow()

        if status == "resolved":
            report.resolved_at = datetime.utcnow()

        self.db.flush()
        logger.info(f"Updated report {incident_id} status to {status}")
        return report

    def get_stats(self) -> Dict[str, Any]:
        """Get USSD report statistics"""
        total = self.db.query(USSDReport).count()
        pending = self.db.query(USSDReport).filter(USSDReport.status == "pending").count()
        high_priority = self.db.query(USSDReport).filter(
            USSDReport.priority.in_(["high", "critical"])
        ).count()

        emergencies = self.db.query(USSDReport).filter(USSDReport.report_type == "emergency").count()
        sightings = self.db.query(USSDReport).filter(USSDReport.report_type == "sighting").count()
        past_incidents = self.db.query(USSDReport).filter(USSDReport.report_type == "past_incident").count()

        return {
            "total_reports": total,
            "pending_reports": pending,
            "high_priority_reports": high_priority,
            "emergency_reports": emergencies,
            "sighting_reports": sightings,
            "past_incident_reports": past_incidents
        }


# =============================================================================
# SMS Repository
# =============================================================================

class SMSReportRepository:
    """Repository for SMS Report operations"""

    def __init__(self, db: Session):
        self.db = db

    def generate_incident_id(self) -> str:
        """Generate next incident ID (SMS-0001 format)"""
        last_report = self.db.query(SMSReport).order_by(
            desc(SMSReport.created_at)
        ).first()

        if last_report and last_report.incident_id:
            try:
                last_num = int(last_report.incident_id.split("-")[1])
                return f"SMS-{str(last_num + 1).zfill(4)}"
            except (IndexError, ValueError):
                pass

        return "SMS-0001"

    def create(self, data: Dict[str, Any]) -> SMSReport:
        """Create a new SMS report"""
        incident_id = self.generate_incident_id()

        report = SMSReport(
            incident_id=incident_id,
            **data
        )

        self.db.add(report)
        self.db.flush()
        logger.info(f"Created SMS report: {incident_id}")
        return report

    def get_by_id(self, incident_id: str) -> Optional[SMSReport]:
        """Get report by incident ID"""
        return self.db.query(SMSReport).filter(
            SMSReport.incident_id == incident_id
        ).first()

    def get_by_phone(self, phone_number: str, limit: int = 10) -> List[SMSReport]:
        """Get reports by phone number"""
        return self.db.query(SMSReport).filter(
            SMSReport.phone_number == phone_number
        ).order_by(desc(SMSReport.created_at)).limit(limit).all()

    def get_pending_review(self, limit: int = 50) -> List[SMSReport]:
        """Get reports that need review"""
        return self.db.query(SMSReport).filter(
            SMSReport.needs_review == True
        ).order_by(desc(SMSReport.created_at)).limit(limit).all()

    def get_high_priority_pending(self) -> List[SMSReport]:
        """Get high/critical priority pending reports"""
        return self.db.query(SMSReport).filter(
            and_(
                SMSReport.status == "pending",
                SMSReport.priority.in_(["high", "critical"])
            )
        ).order_by(desc(SMSReport.created_at)).all()

    def update_status(
        self,
        incident_id: str,
        status: str,
        confirmation_sent: bool = None,
        rangers_alerted: bool = None
    ) -> Optional[SMSReport]:
        """Update report status"""
        report = self.get_by_id(incident_id)
        if not report:
            return None

        report.status = status
        if confirmation_sent is not None:
            report.confirmation_sent = confirmation_sent
        if rangers_alerted is not None:
            report.rangers_alerted = rangers_alerted

        self.db.flush()
        return report

    def get_stats(self) -> Dict[str, Any]:
        """Get SMS report statistics"""
        total = self.db.query(SMSReport).count()
        pending = self.db.query(SMSReport).filter(SMSReport.status == "pending").count()
        needs_review = self.db.query(SMSReport).filter(SMSReport.needs_review == True).count()
        high_priority = self.db.query(SMSReport).filter(
            SMSReport.priority.in_(["high", "critical"])
        ).count()

        return {
            "total": total,
            "pending": pending,
            "needs_review": needs_review,
            "high_priority": high_priority
        }


class SMSConversationRepository:
    """Repository for SMS Conversation operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_active(self, phone_number: str) -> Optional[SMSConversation]:
        """Get active conversation for phone number"""
        return self.db.query(SMSConversation).filter(
            and_(
                SMSConversation.phone_number == phone_number,
                SMSConversation.expires_at > datetime.utcnow()
            )
        ).first()

    def create(
        self,
        phone_number: str,
        original_message: str,
        session_state: str = "new",
        partial_data: Dict = None
    ) -> SMSConversation:
        """Create a new conversation"""
        expires_at = datetime.utcnow() + timedelta(minutes=settings.session_timeout_minutes)

        conversation = SMSConversation(
            phone_number=phone_number,
            original_message=original_message,
            session_state=session_state,
            partial_data=partial_data or {},
            expires_at=expires_at
        )

        self.db.add(conversation)
        self.db.flush()
        return conversation

    def update(
        self,
        conversation: SMSConversation,
        session_state: str = None,
        partial_data: Dict = None
    ) -> SMSConversation:
        """Update conversation state"""
        if session_state:
            conversation.session_state = session_state
        if partial_data:
            conversation.partial_data = {
                **(conversation.partial_data or {}),
                **partial_data
            }
        conversation.updated_at = datetime.utcnow()
        # Extend expiry
        conversation.expires_at = datetime.utcnow() + timedelta(
            minutes=settings.session_timeout_minutes
        )
        self.db.flush()
        return conversation

    def delete(self, conversation: SMSConversation):
        """Delete conversation (after completion)"""
        self.db.delete(conversation)
        self.db.flush()

    def cleanup_expired(self) -> int:
        """Clean up expired conversations"""
        result = self.db.query(SMSConversation).filter(
            SMSConversation.expires_at < datetime.utcnow()
        ).delete()
        self.db.flush()
        return result


class SMSMessageRepository:
    """Repository for SMS Message logging"""

    def __init__(self, db: Session):
        self.db = db

    def log_incoming(
        self,
        message_id: str,
        phone_number: str,
        message_text: str,
        extracted_data: Dict = None
    ) -> SMSMessage:
        """Log incoming SMS"""
        message = SMSMessage(
            message_id=message_id,
            direction="incoming",
            phone_number=phone_number,
            message_text=message_text,
            extracted_data=extracted_data,
            status="received"
        )
        self.db.add(message)
        self.db.flush()
        return message

    def log_outgoing(
        self,
        message_id: str,
        phone_number: str,
        message_text: str,
        linked_report_id: str = None
    ) -> SMSMessage:
        """Log outgoing SMS"""
        message = SMSMessage(
            message_id=message_id or str(uuid.uuid4()),
            direction="outgoing",
            phone_number=phone_number,
            message_text=message_text,
            linked_report_id=linked_report_id,
            status="sent"
        )
        self.db.add(message)
        self.db.flush()
        return message

    def get_messages(
        self,
        phone_number: str = None,
        direction: str = None,
        limit: int = 50
    ) -> List[SMSMessage]:
        """Get messages with optional filters"""
        query = self.db.query(SMSMessage)

        if phone_number:
            query = query.filter(SMSMessage.phone_number == phone_number)
        if direction:
            query = query.filter(SMSMessage.direction == direction)

        return query.order_by(desc(SMSMessage.created_at)).limit(limit).all()

    def get_stats(self) -> Dict[str, Any]:
        """Get message statistics"""
        total = self.db.query(SMSMessage).count()
        incoming = self.db.query(SMSMessage).filter(
            SMSMessage.direction == "incoming"
        ).count()
        outgoing = self.db.query(SMSMessage).filter(
            SMSMessage.direction == "outgoing"
        ).count()

        return {
            "total": total,
            "incoming": incoming,
            "outgoing": outgoing
        }
