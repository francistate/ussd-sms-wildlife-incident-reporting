"""
Helper functions for USSD app
"""
import re
from datetime import datetime
from typing import Tuple


def validate_text_input(text: str, field_type: str) -> Tuple[bool, str, str]:
    """
    Validate user free-text input
    Returns: (is_valid, cleaned_text, error_message)
    """
    text = text.strip()

    if len(text) < 2:
        return False, "", "Too short. Min 2 characters"

    max_len = 30 if field_type == 'species' else 50
    if len(text) > max_len:
        return False, "", f"Too long. Max {max_len} chars"

    # Allow letters, numbers, spaces, basic punctuation
    if not re.match(r'^[A-Za-z0-9\s\-\.,\']+$', text):
        return False, "", "Only letters, numbers, spaces allowed"

    return True, text.title(), ""


def calculate_time_of_day(timestamp: datetime) -> str:
    """Auto-calculate time of day from timestamp"""
    hour = timestamp.hour
    if 4 <= hour < 7:
        return 'dawn'
    elif 7 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 20:
        return 'evening'
    else:
        return 'night'


def calculate_priority(report_data: dict) -> str:
    """Auto-calculate priority based on incident type and severity"""
    incident_type = report_data.get('incident_type')
    severity = report_data.get('severity', 'minor')

    # Critical priority
    if incident_type == 'human_injury':
        return 'critical'

    if incident_type == 'dangerous_behavior':
        if report_data.get('details', {}).get('people_at_risk'):
            return 'critical'
        return 'high'

    # High priority
    if severity == 'severe':
        return 'high'

    # Medium priority
    if report_data.get('report_type') == 'emergency':
        return 'medium'

    # Low priority
    if report_data.get('report_type') in ['past_incident', 'sighting']:
        return 'low'

    return 'medium'
