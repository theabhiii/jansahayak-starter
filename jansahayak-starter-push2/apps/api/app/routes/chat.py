from fastapi import APIRouter

from ..models.schemas import ChatRequest, ChatResponse, FeedbackRequest
from ..services.orchestrator import Orchestrator
from ..utils.language import normalize_language_code

router = APIRouter(prefix="/chat", tags=["chat"])
orchestrator = Orchestrator()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest):
    return orchestrator.answer(
        message=payload.message,
        session_id=payload.session_id,
        channel=payload.channel,
        language_code=payload.language_code,
        location_hint=payload.location_hint,
    )


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
