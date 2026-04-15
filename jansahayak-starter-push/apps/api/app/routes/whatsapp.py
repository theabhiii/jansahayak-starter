from fastapi import APIRouter

from ..models.schemas import WhatsAppWebhookRequest
from ..services.orchestrator import Orchestrator

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
orchestrator = Orchestrator()


@router.post("/webhook")
def webhook(payload: WhatsAppWebhookRequest):
    response = orchestrator.answer(
        message=payload.message,
        session_id=payload.from_number,
        channel="whatsapp",
        language_code=None,
        location_hint=None,
    )
    return {
        "to": payload.from_number,
        "channel": "whatsapp-mock",
        "reply": response["answer"],
        "meta": {
            "detected_language": response["detected_language"],
            "location": response["location"],
        },
    }
