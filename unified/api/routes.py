"""
API Routes for SMS functionality
"""
from fastapi import APIRouter, Form, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from api.schemas import (
    SendSMSRequest, ConfirmationRequest, RangerAlertRequest,
    SMSResponse, ReportResponse, ReportListResponse,
    MessageResponse, MessageListResponse, StatsResponse, ExtractionResponse, HealthResponse
)
from database.connection import get_db_session, check_connection
from database.repository import SMSReportRepository, SMSMessageRepository
from nlp.extractor import extract_from_sms, ExtractionResult
from sms_services.sms_service import get_sms_service
from sms_services.notification_service import (
    send_confirmation, send_ranger_alert, send_use_ussd,
    send_help, send_default_response, should_alert_rangers
)
from sms_services.llm_service import extract_with_llm, merge_llm_result
from config import settings

logger = logging.getLogger(__name__)

sms_router = APIRouter(tags=["SMS"])


# ============ HEALTH & INFO ============

@sms_router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    sms = get_sms_service()
    db_ok = check_connection()

    return HealthResponse(
        service="Wildlife Conservation SMS API",
        status="running",
        version="2.0.0",
        sms_enabled=sms is not None,
        database_connected=db_ok,
        environment=settings.environment
    )


# ============ SMS SENDING ============

@sms_router.post("/sms/send", response_model=SMSResponse)
async def send_sms(request: SendSMSRequest):
    """Send SMS to one or more recipients"""
    sms = get_sms_service()
    if not sms:
        raise HTTPException(status_code=503, detail="SMS service not available")

    result = sms.send_sms(
        message=request.message,
        recipients=request.recipients,
        sender_id=request.sender_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send SMS")
        )

    return SMSResponse(
        success=True,
        message=f"SMS sent to {len(request.recipients)} recipients",
        data={"response": result.get("response")}
    )


@sms_router.post("/sms/incident/confirmation", response_model=SMSResponse)
async def send_incident_confirmation(request: ConfirmationRequest):
    """Send incident confirmation SMS to reporter"""
    success = send_confirmation(
        phone_number=request.phone_number,
        incident_id=request.incident_id,
        incident_type=request.incident_type,
        location=request.location
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send confirmation")

    return SMSResponse(
        success=True,
        message=f"Confirmation sent to {request.phone_number}"
    )


@sms_router.post("/sms/incident/alert", response_model=SMSResponse)
async def send_incident_alert(request: RangerAlertRequest):
    """Send alert SMS to rangers"""
    result = send_ranger_alert(
        ranger_phones=request.ranger_phones,
        incident_id=request.incident_id,
        incident_type=request.incident_type,
        species=request.species,
        location=request.location,
        priority=request.priority
    )

    if not result.get("success"):
        if result.get("skipped"):
            return SMSResponse(
                success=True,
                message=f"Alert skipped: {result.get('reason')}"
            )
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send alerts")
        )

    return SMSResponse(
        success=True,
        message=f"Alert sent to {result.get('recipients')} rangers"
    )


# ============ SMS RECEIVING (WEBHOOK) ============

@sms_router.post("/sms/incoming")
async def receive_sms(
    date: str = Form(...),
    from_: str = Form(..., alias="from"),
    id: str = Form(...),
    linkId: str = Form(None),
    text: str = Form(...),
    to: str = Form(...),
    networkCode: str = Form(None),
    db: Session = Depends(get_db_session)
):
    """
    Webhook endpoint for receiving incoming SMS from Africa's Talking

    This is the main entry point for SMS-based incident reporting.
    """
    logger.info(f"Received SMS from {from_}: {text[:50]}...")

    msg_repo = SMSMessageRepository(db)
    report_repo = SMSReportRepository(db)

    # Log incoming message
    msg_repo.log_incoming(
        message_id=id,
        phone_number=from_,
        message_text=text
    )

    text_lower = text.lower().strip()

    # Check for help command
    if text_lower in ["help", "info", "start", "?"]:
        send_help(from_)
        return {"status": "received", "action": "help_sent"}

    # Extract incident information from message
    extraction = extract_from_sms(text)

    # Check confidence and decide action
    if extraction.overall_confidence >= settings.confidence_threshold_high:
        # High confidence - create report directly
        report = await _create_report(extraction, from_, text, db, report_repo)

        # Send confirmation
        send_confirmation(
            phone_number=from_,
            incident_id=report.incident_id,
            incident_type=report.incident_type,
            location=report.location_name
        )

        # Alert rangers if high priority
        if should_alert_rangers(report.priority):
            # TODO: Get ranger phones from database
            # placeholder for now
            pass

        return {
            "status": "received",
            "action": "report_created",
            "incident_id": report.incident_id
        }

    elif extraction.overall_confidence >= settings.confidence_threshold_low:
        # Medium confidence - try LLM enhancement
        llm_result = await extract_with_llm(text, use_api=settings.hf_use_api)

        if llm_result.success and llm_result.confidence > extraction.overall_confidence * 100:
            # LLM improved the extraction
            merged = merge_llm_result(extraction.to_dict(), llm_result)
            extraction_data = merged
        else:
            extraction_data = extraction.to_dict()

        # Create report with needs_review flag
        report = await _create_report_from_dict(
            extraction_data, from_, text, db, report_repo,
            needs_review=True,
            review_reason="Medium confidence extraction"
        )

        send_confirmation(
            phone_number=from_,
            incident_id=report.incident_id,
            incident_type=report.incident_type,
            location=report.location_name
        )

        return {
            "status": "received",
            "action": "report_created_review",
            "incident_id": report.incident_id
        }

    else:
        # Low confidence - try LLM first
        llm_result = await extract_with_llm(text, use_api=settings.hf_use_api)

        if llm_result.success and llm_result.confidence >= 50:
            # LLM succeeded - create report with review flag
            report = await _create_report_from_llm(
                llm_result, from_, text, db, report_repo
            )

            send_confirmation(
                phone_number=from_,
                incident_id=report.incident_id,
                incident_type=report.incident_type,
                location=report.location_name
            )

            return {
                "status": "received",
                "action": "report_created_llm",
                "incident_id": report.incident_id
            }

        # Both failed - ask user to use USSD
        send_use_ussd(from_)

        return {
            "status": "received",
            "action": "ussd_redirect"
        }


async def _create_report(
    extraction: ExtractionResult,
    phone_number: str,
    original_message: str,
    db: Session,
    report_repo: SMSReportRepository
):
    """Create report from extraction result"""
    priority = _calculate_priority(extraction)

    report = report_repo.create({
        "phone_number": phone_number,
        "species": extraction.species.value,
        "species_confidence": extraction.species.confidence,
        "incident_type": extraction.incident_type.value,
        "incident_type_confidence": extraction.incident_type.confidence,
        "location_name": extraction.location.value,
        "location_confidence": extraction.location.confidence,
        "animal_count": extraction.animal_count.value,
        "severity": extraction.severity.value,
        "original_message": original_message,
        "extracted_data": extraction.to_dict(),
        "priority": priority,
        "extraction_method": extraction.extraction_method,
        "overall_confidence": extraction.overall_confidence
    })

    db.commit()
    return report


async def _create_report_from_dict(
    extraction_data: dict,
    phone_number: str,
    original_message: str,
    db: Session,
    report_repo: SMSReportRepository,
    needs_review: bool = False,
    review_reason: str = None
):
    """Create report from extraction dictionary"""
    species_data = extraction_data.get("species", {})
    incident_data = extraction_data.get("incident_type", {})
    location_data = extraction_data.get("location", {})
    count_data = extraction_data.get("animal_count", {})
    severity_data = extraction_data.get("severity", {})

    priority = _calculate_priority_from_dict(extraction_data)

    report = report_repo.create({
        "phone_number": phone_number,
        "species": species_data.get("value"),
        "species_confidence": species_data.get("confidence", 0),
        "incident_type": incident_data.get("value"),
        "incident_type_confidence": incident_data.get("confidence", 0),
        "location_name": location_data.get("value"),
        "location_confidence": location_data.get("confidence", 0),
        "animal_count": count_data.get("value"),
        "severity": severity_data.get("value"),
        "original_message": original_message,
        "extracted_data": extraction_data,
        "priority": priority,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "extraction_method": extraction_data.get("extraction_method", "hybrid"),
        "overall_confidence": extraction_data.get("overall_confidence", 0)
    })

    db.commit()
    return report


async def _create_report_from_llm(
    llm_result,
    phone_number: str,
    original_message: str,
    db: Session,
    report_repo: SMSReportRepository
):
    """Create report from LLM extraction result"""
    priority = "medium"
    if llm_result.incident_type == "human_injury":
        priority = "critical"
    elif llm_result.incident_type in ["dangerous_animal", "livestock_attack"]:
        priority = "high" if llm_result.severity == "severe" else "medium"

    report = report_repo.create({
        "phone_number": phone_number,
        "species": llm_result.species,
        "species_confidence": llm_result.confidence / 100,
        "incident_type": llm_result.incident_type,
        "incident_type_confidence": llm_result.confidence / 100,
        "location_name": llm_result.location,
        "location_confidence": llm_result.confidence / 100,
        "animal_count": llm_result.animal_count,
        "severity": llm_result.severity,
        "original_message": original_message,
        "extracted_data": {
            "species": llm_result.species,
            "incident_type": llm_result.incident_type,
            "location": llm_result.location,
            "animal_count": llm_result.animal_count,
            "severity": llm_result.severity,
            "llm_confidence": llm_result.confidence
        },
        "priority": priority,
        "needs_review": True,
        "review_reason": "LLM extraction only",
        "extraction_method": "llm",
        "overall_confidence": llm_result.confidence / 100
    })

    db.commit()
    return report


def _calculate_priority(extraction: ExtractionResult) -> str:
    """Calculate priority from extraction result"""
    if extraction.incident_type.value == "human_injury":
        return "critical"

    if extraction.incident_type.value == "dangerous_animal":
        if extraction.severity.value == "severe":
            return "critical"
        return "high"

    if extraction.incident_type.value == "livestock_attack":
        if extraction.severity.value == "severe":
            return "high"
        return "medium"

    if extraction.severity.value == "severe":
        return "medium"

    return "low"


def _calculate_priority_from_dict(data: dict) -> str:
    """Calculate priority from extraction dictionary"""
    incident_type = data.get("incident_type", {}).get("value")
    severity = data.get("severity", {}).get("value")

    if incident_type == "human_injury":
        return "critical"

    if incident_type == "dangerous_animal":
        if severity == "severe":
            return "critical"
        return "high"

    if incident_type == "livestock_attack":
        if severity == "severe":
            return "high"
        return "medium"

    if severity == "severe":
        return "medium"

    return "low"


# ============ REPORTS ============

@sms_router.get("/sms/reports", response_model=ReportListResponse)
async def get_reports(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    needs_review: Optional[bool] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db_session)
):
    """Get SMS reports with optional filters"""
    from database.models import SMSReport

    query = db.query(SMSReport)

    if status:
        query = query.filter(SMSReport.status == status)
    if priority:
        query = query.filter(SMSReport.priority == priority)
    if needs_review is not None:
        query = query.filter(SMSReport.needs_review == needs_review)

    reports = query.order_by(SMSReport.created_at.desc()).limit(limit).all()

    return ReportListResponse(
        total=len(reports),
        reports=[ReportResponse(
            incident_id=r.incident_id,
            phone_number=r.phone_number,
            species=r.species,
            incident_type=r.incident_type,
            location_name=r.location_name,
            severity=r.severity,
            priority=r.priority,
            status=r.status,
            needs_review=r.needs_review,
            overall_confidence=r.overall_confidence or 0,
            created_at=r.created_at
        ) for r in reports]
    )


@sms_router.get("/sms/reports/{incident_id}", response_model=ReportResponse)
async def get_report(
    incident_id: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific SMS report"""
    repo = SMSReportRepository(db)
    report = repo.get_by_id(incident_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        incident_id=report.incident_id,
        phone_number=report.phone_number,
        species=report.species,
        incident_type=report.incident_type,
        location_name=report.location_name,
        severity=report.severity,
        priority=report.priority,
        status=report.status,
        needs_review=report.needs_review,
        overall_confidence=report.overall_confidence or 0,
        created_at=report.created_at
    )


# ============ MESSAGES ============

@sms_router.get("/sms/messages", response_model=MessageListResponse)
async def get_messages(
    direction: Optional[str] = None,
    phone_number: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db_session)
):
    """Get SMS messages"""
    repo = SMSMessageRepository(db)
    messages = repo.get_messages(
        phone_number=phone_number,
        direction=direction,
        limit=limit
    )
    stats = repo.get_stats()

    return MessageListResponse(
        total=stats["total"],
        incoming=stats["incoming"],
        outgoing=stats["outgoing"],
        messages=[MessageResponse(
            id=str(m.id),
            direction=m.direction,
            phone_number=m.phone_number,
            message_text=m.message_text,
            status=m.status,
            created_at=m.created_at
        ) for m in messages]
    )


# ============ STATS ============

@sms_router.get("/sms/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db_session)):
    """Get SMS statistics"""
    report_repo = SMSReportRepository(db)
    msg_repo = SMSMessageRepository(db)

    return StatsResponse(
        reports=report_repo.get_stats(),
        messages=msg_repo.get_stats()
    )


# ============ DELIVERY REPORTS (WEBHOOK) ============

@sms_router.post("/sms/delivery")
async def delivery_report(
    id: str = Form(...),
    status: str = Form(...),
    phoneNumber: str = Form(None),
    networkCode: str = Form(None),
    failureReason: str = Form(None),
    db: Session = Depends(get_db_session)
):
    """
    Webhook endpoint for SMS delivery reports from Africa's Talking

    Status values:
    - Success: Message delivered to recipient
    - Sent: Message sent to carrier
    - Buffered: Message queued for delivery
    - Rejected: Message rejected by carrier
    - Failed: Message delivery failed

    Configure this URL in Africa's Talking:
    SMS → SMS Callback URLs → Delivery Reports
    """
    logger.info(f"Delivery report: {id} -> {status} (phone: {phoneNumber})")

    # Update message status in database
    from database.models import SMSMessage

    message = db.query(SMSMessage).filter(
        SMSMessage.message_id == id
    ).first()

    if message:
        message.status = status.lower()
        if failureReason:
            # Store failure reason in extracted_data
            message.extracted_data = {
                **(message.extracted_data or {}),
                "failure_reason": failureReason,
                "network_code": networkCode
            }
        db.commit()
        logger.info(f"Updated message {id} status to {status}")
    else:
        logger.warning(f"Message {id} not found for delivery report")

    return {
        "status": "received",
        "message_id": id,
        "delivery_status": status
    }


@sms_router.get("/sms/delivery/stats")
async def get_delivery_stats(db: Session = Depends(get_db_session)):
    """Get delivery statistics for outgoing messages"""
    from database.models import SMSMessage
    from sqlalchemy import func

    # Count by status
    stats = db.query(
        SMSMessage.status,
        func.count(SMSMessage.id).label('count')
    ).filter(
        SMSMessage.direction == 'outgoing'
    ).group_by(SMSMessage.status).all()

    status_counts = {s.status or 'unknown': s.count for s in stats}

    total = sum(status_counts.values())
    delivered = status_counts.get('success', 0)
    failed = status_counts.get('failed', 0) + status_counts.get('rejected', 0)

    return {
        "total_sent": total,
        "delivered": delivered,
        "failed": failed,
        "delivery_rate": round(delivered / total * 100, 2) if total > 0 else 0,
        "by_status": status_counts
    }


# ============ TESTING/DEBUG ============

@sms_router.post("/sms/test/extract", response_model=ExtractionResponse)
async def test_extraction(message: str):
    """Test NLP extraction on a message (for debugging)"""
    extraction = extract_from_sms(message)

    return ExtractionResponse(
        species={"value": extraction.species.value, "confidence": extraction.species.confidence},
        incident_type={"value": extraction.incident_type.value, "confidence": extraction.incident_type.confidence},
        location={"value": extraction.location.value, "confidence": extraction.location.confidence},
        animal_count={"value": extraction.animal_count.value, "confidence": extraction.animal_count.confidence},
        severity={"value": extraction.severity.value, "confidence": extraction.severity.confidence},
        overall_confidence=extraction.overall_confidence,
        extraction_method=extraction.extraction_method,
        needs_clarification=extraction.needs_clarification,
        clarification_field=extraction.clarification_field
    )
