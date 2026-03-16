"""
Pydantic models for API request/response schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ REQUEST MODELS ============

class SendSMSRequest(BaseModel):
    """Request to send SMS"""
    message: str = Field(..., min_length=1, max_length=480)
    recipients: List[str] = Field(..., min_items=1)
    sender_id: Optional[str] = None


class ConfirmationRequest(BaseModel):
    """Request to send incident confirmation"""
    phone_number: str
    incident_id: str
    incident_type: str
    location: Optional[str] = None


class RangerAlertRequest(BaseModel):
    """Request to send ranger alert"""
    incident_id: str
    incident_type: str
    species: str
    location: str
    priority: str
    ranger_phones: List[str]


class ClarificationResponse(BaseModel):
    """Response to a clarification question"""
    phone_number: str
    response: str  # "1", "2", etc. or free text


# ============ RESPONSE MODELS ============

class SMSResponse(BaseModel):
    """Generic SMS operation response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ReportResponse(BaseModel):
    """SMS Report response"""
    incident_id: str
    phone_number: str
    species: Optional[str]
    incident_type: Optional[str]
    location_name: Optional[str]
    severity: Optional[str]
    priority: str
    status: str
    needs_review: bool
    overall_confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """List of reports response"""
    total: int
    reports: List[ReportResponse]


class MessageResponse(BaseModel):
    """SMS Message response"""
    id: str
    direction: str
    phone_number: str
    message_text: str
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """List of messages response"""
    total: int
    incoming: int
    outgoing: int
    messages: List[MessageResponse]


class StatsResponse(BaseModel):
    """Statistics response"""
    reports: Dict[str, int]
    messages: Dict[str, int]


class ExtractionResponse(BaseModel):
    """Extraction result response"""
    species: Optional[Dict[str, Any]]
    incident_type: Optional[Dict[str, Any]]
    location: Optional[Dict[str, Any]]
    animal_count: Optional[Dict[str, Any]]
    severity: Optional[Dict[str, Any]]
    overall_confidence: float
    extraction_method: str
    needs_clarification: bool
    clarification_field: Optional[str]


class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str
    version: str
    sms_enabled: bool
    database_connected: bool
    environment: str
