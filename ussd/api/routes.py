"""
API Routes for USSD App
"""
from fastapi import APIRouter, Form, Response, Depends
from sqlalchemy.orm import Session
import logging

from database.connection import get_db_session, check_connection
from database.repository import USSDReportRepository
from services.session_service import get_or_create_session, sessions, parse_ussd_input
from services.menu_handlers import (
    show_main_menu, show_help, handle_invalid_input,
    handle_emergency_incident, handle_wildlife_sighting, handle_past_incident
)
from services.report_service import (
    save_emergency_report, save_sighting_report, save_past_incident_report, reports
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ MAIN USSD ENDPOINT ============

@router.post("/ussd")
async def ussd_handler(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default="")
):
    """
    Main USSD endpoint handler

    Receives requests from Africa's Talking:
    - sessionId: Unique session identifier
    - serviceCode: USSD code dialed
    - phoneNumber: User's phone number
    - text: User's input path (e.g., "1*2*3")
    """
    session = get_or_create_session(sessionId, phoneNumber)
    session["session_id"] = sessionId
    user_input = parse_ussd_input(text)
    session["input_history"] = user_input

    logger.info(f"USSD from {phoneNumber}: {text}")

    # Main menu
    if len(user_input) == 0:
        return Response(content=show_main_menu(), media_type="text/plain")

    main_choice = user_input[0]

    if main_choice == "1":
        # Report Emergency NOW
        response = handle_emergency_incident(session, user_input)

        # Handle submission
        if response == "SUBMIT_EMERGENCY":
            report = save_emergency_report(session)
            response = f"END Report Submitted!\n\n"
            response += f"ID: {report['incident_id']}\n"
            response += f"{report['incident_type'].replace('_', ' ').title()}\n"
            response += f"{report['species']} at {report['location_name']}\n"
            response += f"Priority: {report['priority'].upper()}"

        if "Confirm Report" in response:
            session["last_screen"] = response

        return Response(content=response, media_type="text/plain")

    elif main_choice == "2":
        # Wildlife Sighting
        response = handle_wildlife_sighting(session, user_input)

        if response == "SUBMIT_SIGHTING":
            report = save_sighting_report(session)
            response = f"END Sighting Logged!\n\n"
            response += f"ID: {report['incident_id']}\n"
            response += f"{report['species']} ({report['animal_count']})\n"
            response += f"at {report['location_name']}\n\n"
            response += "Thank you for helping monitor wildlife!"

        return Response(content=response, media_type="text/plain")

    elif main_choice == "3":
        # Past Incident
        response = handle_past_incident(session, user_input)

        if response == "SUBMIT_EMERGENCY":
            report = save_past_incident_report(session)
            response = f"END Past Incident Logged!\n\n"
            response += f"ID: {report['incident_id']}\n"
            response += f"{report['incident_type'].replace('_', ' ').title()}\n"
            response += f"Thank you for reporting!"

        if "Confirm Report" in response:
            session["last_screen"] = response

        return Response(content=response, media_type="text/plain")

    elif main_choice == "4":
        # Help
        return Response(content=show_help(), media_type="text/plain")

    else:
        return Response(content=handle_invalid_input(), media_type="text/plain")


# ============ HEALTH & DEBUG ENDPOINTS ============

@router.get("/")
async def root(db: Session = Depends(get_db_session)):
    """Health check endpoint"""
    db_connected = check_connection()
    db_stats = {}

    if db_connected:
        try:
            repo = USSDReportRepository(db)
            db_stats = repo.get_stats()
        except Exception:
            db_stats = {"error": "Failed to get stats"}

    return {
        "service": "Wildlife Conservation USSD v2",
        "status": "running",
        "version": "2.0.0",
        "database_connected": db_connected,
        "file_reports": len(reports),
        "database_stats": db_stats
    }


@router.get("/health")
async def health():
    """Simple health check"""
    return {
        "status": "healthy",
        "database": check_connection()
    }


@router.get("/sessions")
async def view_sessions():
    """Debug endpoint to view active sessions"""
    return {
        "total_sessions": len(sessions),
        "sessions": {
            sid: {
                "phone": sdata["phone"],
                "last_active": sdata["last_active"].isoformat(),
                "data": sdata.get("data", {}),
                "input_history": sdata.get("input_history", [])
            }
            for sid, sdata in sessions.items()
        }
    }


@router.get("/reports")
async def view_reports(db: Session = Depends(get_db_session)):
    """View all reports"""
    try:
        repo = USSDReportRepository(db)
        db_reports = repo.get_reports(limit=50)
        return {
            "source": "database",
            "total_reports": len(db_reports),
            "reports": [r.to_dict() for r in db_reports]
        }
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return {
            "source": "file",
            "total_reports": len(reports),
            "reports": reports[-10:] if reports else []
        }


@router.get("/reports/pending")
async def view_pending_reports(db: Session = Depends(get_db_session)):
    """View pending high-priority reports"""
    try:
        repo = USSDReportRepository(db)
        pending = repo.get_pending_high_priority()
        return {
            "source": "database",
            "count": len(pending),
            "reports": [r.to_dict() for r in pending]
        }
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        pending = [r for r in reports if r.get("status") == "pending" and r.get("priority") in ["high", "critical"]]
        return {
            "source": "file",
            "count": len(pending),
            "reports": pending
        }
