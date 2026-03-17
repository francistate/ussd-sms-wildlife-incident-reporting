"""
Notification Service
Handles sending incident confirmations and ranger alerts
"""
import logging
from typing import List, Optional, Dict, Any

from sms_services.sms_service import get_sms_service
from sms_services.templates import (
    CONFIRMATION_TEMPLATE, CONFIRMATION_NO_LOCATION, ALERT_TEMPLATE,
    get_unclear_message_template, get_help_template, get_default_response
)
from config import settings

logger = logging.getLogger(__name__)


def format_incident_type(incident_type: str) -> str:
    """Format incident type for display"""
    return incident_type.replace("_", " ").title() if incident_type else "Incident"


def send_confirmation(
    phone_number: str,
    incident_id: str,
    incident_type: str,
    location: Optional[str] = None
) -> bool:
    """
    Send incident confirmation SMS to reporter

    Args:
        phone_number: Reporter's phone number
        incident_id: Incident ID (e.g., SMS-0001)
        incident_type: Type of incident
        location: Location name (optional)

    Returns:
        True if sent successfully
    """
    sms = get_sms_service()
    if not sms:
        logger.warning("SMS service not initialized")
        return False

    if location:
        message = CONFIRMATION_TEMPLATE.format(
            incident_id=incident_id,
            incident_type=format_incident_type(incident_type),
            location=location
        )
    else:
        message = CONFIRMATION_NO_LOCATION.format(
            incident_id=incident_id,
            incident_type=format_incident_type(incident_type)
        )

    result = sms.send_single(message, phone_number)
    success = result.get("success", False)

    if success:
        logger.info(f"Confirmation sent to {phone_number} for {incident_id}")
    else:
        logger.error(f"Failed to send confirmation: {result.get('error')}")

    return success


def send_ranger_alert(
    ranger_phones: List[str],
    incident_id: str,
    incident_type: str,
    species: str,
    location: str,
    priority: str
) -> Dict[str, Any]:
    """
    Send alert SMS to rangers for high-priority incidents

    Args:
        ranger_phones: List of ranger phone numbers
        incident_id: Incident ID
        incident_type: Type of incident
        species: Animal species
        location: Location name
        priority: Priority level

    Returns:
        Dictionary with success status and details
    """
    sms = get_sms_service()
    if not sms:
        logger.warning("SMS service not initialized")
        return {"success": False, "error": "SMS service not initialized"}

    # Only alert for high/critical priority
    if priority.lower() not in settings.alert_priority_threshold:
        logger.info(f"Skipping ranger alert for {priority} priority incident")
        return {"success": True, "skipped": True, "reason": "Low priority"}

    message = ALERT_TEMPLATE.format(
        priority=priority.upper(),
        incident_type=format_incident_type(incident_type),
        species=species or "Unknown",
        location=location or "Unknown",
        incident_id=incident_id
    )

    result = sms.send_sms(message, ranger_phones)
    success = result.get("success", False)

    if success:
        logger.info(f"Alert sent to {len(ranger_phones)} rangers for {incident_id}")
    else:
        logger.error(f"Failed to send ranger alerts: {result.get('error')}")

    return {
        "success": success,
        "recipients": len(ranger_phones),
        "response": result.get("response"),
        "error": result.get("error")
    }


def send_use_ussd(phone_number: str) -> bool:
    """
    Send message asking user to send clearer SMS or use USSD

    Args:
        phone_number: User's phone number

    Returns:
        True if sent successfully
    """
    sms = get_sms_service()
    if not sms:
        logger.warning("SMS service not initialized")
        return False

    result = sms.send_single(get_unclear_message_template(), phone_number)
    return result.get("success", False)


def send_help(phone_number: str) -> bool:
    """Send help message"""
    sms = get_sms_service()
    if not sms:
        return False

    result = sms.send_single(get_help_template(), phone_number)
    return result.get("success", False)


def send_default_response(phone_number: str) -> bool:
    """Send default response for unrecognized messages"""
    sms = get_sms_service()
    if not sms:
        return False

    result = sms.send_single(get_default_response(), phone_number)
    return result.get("success", False)


def should_alert_rangers(priority: str) -> bool:
    """Check if rangers should be alerted based on priority"""
    return priority.lower() in settings.alert_priority_threshold
