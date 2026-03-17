"""
SMS Message Templates
Edit these templates to customize SMS responses
"""

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

# Sent when message couldn't be understood
UNCLEAR_MESSAGE_TEMPLATE = """We couldn't understand your report.
Please send a clearer message including:
- Animal type 
- What happened
- Location"""

# Sent when user requests help
HELP_TEMPLATE = """Wildlife Conservation
Send a message describing the incident.
Example: "elephant destroyed crops at nanyuki"
Include: animal, incident type, and location."""

# Default response for unrecognized messages
DEFAULT_RESPONSE = """Thank you for your message.
Reply HELP for assistance on how to report an incident."""
