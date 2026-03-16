"""
Notification Service
Handles sending incident confirmations and ranger alerts
"""
import logging
from typing import List, Optional, Dict, Any

from services.sms_service import get_sms_service
from config import settings

logger = logging.getLogger(__name__)


# Message templates
CONFIRMATION_TEMPLATE = """Report received!
ID: {incident_id}
{incident_type}
Location: {location}
Rangers have been alerted."""

CONFIRMATION_NO_LOCATION = """Report received!
ID: {incident_id}
{incident_type}
Rangers have been notified."""

ALERT_TEMPLATE = """ALERT [{priority}]
{incident_type}
Animal: {species}
Location: {location}
ID: {incident_id}
Respond ASAP!"""

CLARIFY_SPECIES = """What animal was involved?
Reply with number:
1=Elephant
2=Lion
3=Leopard
4=Buffalo
5=Hyena
6=Other"""

CLARIFY_INCIDENT = """What happened?
Reply with number:
1=Animal attack
2=Crop damage
3=Dangerous animal
4=Property damage
5=Sighting only"""

CLARIFY_LOCATION = """Where did this happen?
Reply with the location name or nearest town."""

HELP_TEMPLATE = """Wildlife Conservation
Send a message describing the incident.
Example: "elephant destroyed crops at nanyuki"
Or dial *384*55# for USSD reporting."""

DEFAULT_RESPONSE = """Thank you for your message.
Reply HELP for assistance or dial *384*55# to report an incident."""


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


def send_clarification(
    phone_number: str,
    clarification_type: str
) -> bool:
    """
    Send clarification question SMS

    Args:
        phone_number: User's phone number
        clarification_type: Type of clarification needed (species, incident_type, location)

    Returns:
        True if sent successfully
    """
    sms = get_sms_service()
    if not sms:
        logger.warning("SMS service not initialized")
        return False

    templates = {
        "species": CLARIFY_SPECIES,
        "incident_type": CLARIFY_INCIDENT,
        "location": CLARIFY_LOCATION
    }

    message = templates.get(clarification_type, CLARIFY_INCIDENT)
    result = sms.send_single(message, phone_number)

    return result.get("success", False)


def send_help(phone_number: str) -> bool:
    """Send help message"""
    sms = get_sms_service()
    if not sms:
        return False

    result = sms.send_single(HELP_TEMPLATE, phone_number)
    return result.get("success", False)


def send_default_response(phone_number: str) -> bool:
    """Send default response for unrecognized messages"""
    sms = get_sms_service()
    if not sms:
        return False

    result = sms.send_single(DEFAULT_RESPONSE, phone_number)
    return result.get("success", False)


def should_alert_rangers(priority: str) -> bool:
    """Check if rangers should be alerted based on priority"""
    return priority.lower() in settings.alert_priority_threshold
