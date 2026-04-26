from fastapi import APIRouter

from ..models.schemas import SpeechToTextRequest, VoiceRequest, VoiceResponse
from ..services.sarvam_service import SarvamService

router = APIRouter(prefix="/voice", tags=["voice"])
service = SarvamService()


@router.post("/tts", response_model=VoiceResponse)
def tts(payload: VoiceRequest):
    result = service.text_to_speech(payload.text, payload.language_code)
    return VoiceResponse(**result)


@router.post("/stt")
def stt(payload: SpeechToTextRequest):
    return service.speech_to_text(
        transcript_hint=payload.transcript_hint,
        language_code=payload.language_code,
        audio_base64=payload.audio_base64,
        mime_type=payload.mime_type,
    )
