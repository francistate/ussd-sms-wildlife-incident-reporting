"""
Database repository for SMS operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import uuid
import logging

from database.models import SMSReport, SMSConversation, SMSMessage
from config import settings

logger = logging.getLogger(__name__)


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
