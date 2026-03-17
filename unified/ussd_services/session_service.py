"""
Session management for USSD
"""
from typing import Dict, Any
from datetime import datetime

# In-memory session storage
sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str, phone_number: str) -> Dict[str, Any]:
    """Get existing session or create new one"""
    if session_id not in sessions:
        sessions[session_id] = {
            "phone": phone_number,
            "data": {"details": {}},
            "last_active": datetime.now()
        }
    else:
        sessions[session_id]["last_active"] = datetime.now()

    return sessions[session_id]


def parse_ussd_input(text: str) -> list:
    """Parse USSD input string into list of choices"""
    if text == "":
        return []
    return text.split("*")


def cleanup_expired_sessions(timeout_minutes: int = 30):
    """Remove expired sessions"""
    from datetime import timedelta
    now = datetime.now()
    expired = [
        sid for sid, data in sessions.items()
        if (now - data["last_active"]) > timedelta(minutes=timeout_minutes)
    ]
    for sid in expired:
        del sessions[sid]
    return len(expired)
