"""
Database repository for USSD operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from geoalchemy2.functions import ST_MakePoint
import logging

from database.models import USSDReport

logger = logging.getLogger(__name__)


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

        # Handle timestamps
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

        # Add location coordinates if provided
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
        """Get report statistics"""
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
