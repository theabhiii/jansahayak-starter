import logging

from fastapi import APIRouter

from ..models.schemas import ChatRequest, ChatResponse, FeedbackRequest
from ..services.orchestrator import Orchestrator
from ..services.sarvam_service import SarvamService
from ..utils.language import normalize_language_code

router = APIRouter(prefix="/chat", tags=["chat"])
orchestrator = Orchestrator()
sarvam = SarvamService()
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest):
    result = orchestrator.answer(
        message=payload.message,
        session_id=payload.session_id,
        channel=payload.channel,
        language_code=payload.language_code,
        location_hint=payload.location_hint,
    )
    try:
        answer = (result.get("answer") or "").strip()
        language_code = result.get("language_code") or result.get("session_language") or "en-IN"
        if answer:
            tts = sarvam.text_to_speech(answer, language_code)
            result["audio_status"] = tts.get("status")
            result["audio_detail"] = tts.get("detail")
            result["audio_base64"] = tts.get("audio_base64")
            result["audio_mime_type"] = tts.get("audio_mime_type")
    except Exception as exc:
        logger.warning("chat_tts_failed session_id=%s err=%s", payload.session_id, str(exc))
        result["audio_status"] = "error"
        result["audio_detail"] = "TTS generation failed"
        result["audio_base64"] = None
        result["audio_mime_type"] = None
    return result


@router.post("/feedback")
def feedback(payload: FeedbackRequest):
    retry_language = normalize_language_code(payload.language_code)
    if not retry_language:
        retry_language = "hi-IN" if any('\u0900' <= ch <= '\u097F' for ch in payload.original_question) else "en-IN"
    improved = orchestrator.retry(
        question=payload.original_question,
        original_answer=payload.original_answer,
        reason=payload.reason or payload.feedback,
        sources=[],
        location={"state": "Unknown", "district": "Unknown"},
        language_code=retry_language,
    )
    return {"status": "ok", "improved_answer": improved}
