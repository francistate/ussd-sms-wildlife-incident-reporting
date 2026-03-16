"""
Report service for saving USSD reports
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from database.connection import get_db
from database.repository import USSDReportRepository
from services.helpers import calculate_time_of_day, calculate_priority

logger = logging.getLogger(__name__)

# File backup
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_FILE = DATA_DIR / "reports.json"

# In-memory reports (for file backup)
reports: list = []


def load_reports() -> list:
    """Load reports from JSON file"""
    if REPORTS_FILE.exists():
        try:
            with open(REPORTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading reports: {e}")
            return []
    return []


def save_reports_to_file():
    """Save reports to JSON file"""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(REPORTS_FILE, "w") as f:
            json.dump(reports, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving reports: {e}")
        return False


def generate_incident_id(report_type: str) -> str:
    """Generate incident ID"""
    count = len(reports) + 1
    prefix = "INC" if report_type in ['emergency', 'past_incident'] else "SIG"
    return f"{prefix}-{count:04d}"


def save_emergency_report(session: Dict[str, Any]) -> dict:
    """Save emergency report to database and file backup"""
    data = session["data"]

    incident_id = generate_incident_id('emergency')

    priority = calculate_priority({
        'report_type': 'emergency',
        'incident_type': data.get('incident_type'),
        'severity': data.get('severity'),
        'details': data.get('details', {})
    })

    now = datetime.now()
    report = {
        "incident_id": incident_id,
        "report_type": "emergency",
        "incident_type": data.get("incident_type"),
        "phone_number": session["phone"],
        "species": data.get("species"),
        "species_is_other": data.get("species_is_other", False),
        "animal_count": data.get("animal_count"),
        "location_name": data.get("location_name"),
        "location_is_other": data.get("location_is_other", False),
        "severity": data.get("severity"),
        "priority": priority,
        "weather": None,
        "time_of_day": calculate_time_of_day(now),
        "details": data.get("details", {}),
        "status": "pending",
        "reported_at": now.isoformat(),
        "occurred_at": now.isoformat(),
        "session_id": session.get("session_id")
    }

    # Save to database
    try:
        with get_db() as db:
            repo = USSDReportRepository(db)
            db_report = repo.create(report)
            report["incident_id"] = db_report.incident_id
            logger.info(f"Report {report['incident_id']} saved to database")
    except Exception as e:
        logger.error(f"Database save failed: {e}")

    # Also save to file as backup
    reports.append(report)
    save_reports_to_file()

    return report


def save_sighting_report(session: Dict[str, Any]) -> dict:
    """Save wildlife sighting to database and file backup"""
    data = session["data"]

    incident_id = generate_incident_id('sighting')

    now = datetime.now()
    report = {
        "incident_id": incident_id,
        "report_type": "sighting",
        "incident_type": "sighting",
        "phone_number": session["phone"],
        "species": data.get("species"),
        "species_is_other": data.get("species_is_other", False),
        "animal_count": data.get("animal_count"),
        "location_name": data.get("location_name"),
        "location_is_other": data.get("location_is_other", False),
        "severity": None,
        "priority": "low",
        "weather": data.get("weather"),
        "time_of_day": calculate_time_of_day(now),
        "details": {
            "behavior": data.get("behavior")
        },
        "status": "logged",
        "reported_at": now.isoformat(),
        "occurred_at": now.isoformat(),
        "session_id": session.get("session_id")
    }

    # Save to database
    try:
        with get_db() as db:
            repo = USSDReportRepository(db)
            db_report = repo.create(report)
            report["incident_id"] = db_report.incident_id
            logger.info(f"Sighting {report['incident_id']} saved to database")
    except Exception as e:
        logger.error(f"Database save failed: {e}")

    # Also save to file as backup
    reports.append(report)
    save_reports_to_file()

    return report


def save_past_incident_report(session: Dict[str, Any]) -> dict:
    """Save past incident report"""
    # First save as emergency
    report = save_emergency_report(session)

    # Adjust for past incident
    report["report_type"] = "past_incident"
    report["priority"] = "low"

    # Calculate occurred_at based on when
    occurred_when = session["data"].get("occurred_when", "yesterday")
    if occurred_when == "yesterday":
        report["occurred_at"] = (datetime.now() - timedelta(days=1)).isoformat()
    elif occurred_when == "2-7_days":
        report["occurred_at"] = (datetime.now() - timedelta(days=3)).isoformat()
    else:
        report["occurred_at"] = (datetime.now() - timedelta(days=14)).isoformat()

    # Update file
    save_reports_to_file()

    return report


# Load reports on module import
reports = load_reports()
