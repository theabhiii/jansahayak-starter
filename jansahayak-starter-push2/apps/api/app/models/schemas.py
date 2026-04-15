from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    channel: str = Field(default="web")
    session_id: str = Field(default="demo-session")
    language_code: Optional[str] = None
    location_hint: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    session_language: str
    language_code: str
    detected_language: str
    detection_confidence: float
    location: Dict[str, Any]
    answer: str
    sources: List[Dict[str, Any]]
    actions: List[str]
    feedback_token: str
    language_trace: Dict[str, Any]


class FeedbackRequest(BaseModel):
    session_id: str
    feedback_token: str
    original_question: str
    original_answer: str
    feedback: str
    reason: Optional[str] = None
    language_code: Optional[str] = None


class VoiceRequest(BaseModel):
    text: str
    language_code: str = Field(default="en-IN")


class VoiceResponse(BaseModel):
    status: str
    detail: str
    audio_base64: Optional[str] = None


class SpeechToTextRequest(BaseModel):
    transcript_hint: Optional[str] = None
    language_code: Optional[str] = None


class WhatsAppWebhookRequest(BaseModel):
    from_number: str
    message: str
    name: Optional[str] = None


class SchemeRecord(BaseModel):
    id: str
    title: str
    category: str
    level: str
    states: List[str]
    districts: List[str]
    eligibility: str
    benefits: str
    application: str
    grievance_office: str
    languages: List[str]
    source_url: str
