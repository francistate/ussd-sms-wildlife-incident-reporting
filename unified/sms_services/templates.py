"""
SMS Message Templates for Unified App
Edit these templates to customize SMS responses
"""
from config import settings

# Sent when a report is successfully created
CONFIRMATION_TEMPLATE = """Report received!
ID: {incident_id}
{incident_type}
Location: {location}
Rangers have been alerted."""

# Sent when report created but no location extracted
CONFIRMATION_NO_LOCATION = """Report received!
ID: {incident_id}
{incident_type}
Rangers have been notified."""

# Sent to rangers for high-priority incidents
ALERT_TEMPLATE = """ALERT [{priority}]
{incident_type}
Animal: {species}
Location: {location}
ID: {incident_id}
Respond ASAP!"""


def get_unclear_message_template() -> str:
    """Get unclear message template with current USSD code"""
    return f"""We couldn't fully understand your report.
Please send a clearer message like: "elephant destroyed crops at nanyuki"
Or dial {settings.ussd_code} for USSD reporting."""


def get_help_template() -> str:
    """Get help template with current USSD code"""
    return f"""Wildlife Conservation
Send a message describing the incident.
Example: "elephant destroyed crops at nanyuki"
Or dial {settings.ussd_code} for USSD reporting."""


def get_default_response() -> str:
    """Get default response with current USSD code"""
    return f"""Thank you for your message.
Reply HELP for assistance or dial {settings.ussd_code} to report an incident."""
