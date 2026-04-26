import base64
import logging
from pathlib import Path
import time
import uuid as _uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from xml.sax.saxutils import escape

from ..core.config import get_settings
from ..models.schemas import WhatsAppWebhookRequest
from ..services.orchestrator import Orchestrator
from ..services.sarvam_service import SarvamService

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
orchestrator = Orchestrator()
sarvam = SarvamService()
logger = logging.getLogger(__name__)
_PUBLIC_AUDIO_DIR = Path(__file__).resolve().parents[4] / "public" / "audio"
_PUBLIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
_AUDIO_TTL_SECONDS = 60 * 60
_pending_follow_up_options: dict[str, list[dict[str, str]]] = {}
_pending_language_selection: dict[str, bool] = {}
_pending_initial_message: dict[str, str] = {}
_pending_feedback: dict[str, dict[str, object]] = {}
_pending_pincode_input: dict[str, bool] = {}
_session_reply_audio_enabled: dict[str, bool] = {}

_LANGUAGE_CHOICES: list[dict[str, str]] = [
    {"value": "en-IN", "label": "English"},
    {"value": "hi-IN", "label": "Hindi"},
    {"value": "ta-IN", "label": "Tamil"},
    {"value": "te-IN", "label": "Telugu"},
    {"value": "kn-IN", "label": "Kannada"},
    {"value": "ml-IN", "label": "Malayalam"},
    {"value": "mr-IN", "label": "Marathi"},
    {"value": "gu-IN", "label": "Gujarati"},
    {"value": "bn-IN", "label": "Bengali"},
    {"value": "ur-IN", "label": "Urdu"},
]

_FEEDBACK_REASON_CHOICES: list[dict[str, str]] = [
    {"value": "simpler", "label": "Need simpler explanation"},
    {"value": "not_relevant", "label": "Not relevant to my issue"},
    {"value": "wrong_language", "label": "Wrong language"},
    {"value": "missing_steps", "label": "Missing steps/documents"},
]
_TWILIO_MESSAGE_CHAR_LIMIT = 1400

_UI_STRINGS: dict[str, dict[str, str]] = {
    "en-IN": {
        "reply_with_number": "Reply with a number:",
        "select_language": "Please select your preferred language:",
        "helpful_prompt": "Was this answer helpful?",
        "feedback_reason_prompt": "Please share the reason (reply with a number):",
        "feedback_thanks": "Thanks for your feedback. You can ask your next question.",
        "end_session": "0. End session",
        "session_ended": "Session ended. You can start a fresh chat anytime by sending a new message.",
        "language_set": "Language set to {label}.",
        "yes": "Yes",
        "no": "No",
    },
    "hi-IN": {
        "reply_with_number": "कृपया नंबर से जवाब दें:",
        "select_language": "कृपया अपनी पसंदीदा भाषा चुनें:",
        "helpful_prompt": "क्या यह जवाब मददगार था?",
        "feedback_reason_prompt": "कृपया कारण बताएं (नंबर से जवाब दें):",
        "feedback_thanks": "धन्यवाद। आप अगला सवाल पूछ सकते हैं।",
        "end_session": "0. सत्र समाप्त करें",
        "session_ended": "सत्र समाप्त कर दिया गया है। नई चैट शुरू करने के लिए नया संदेश भेजें।",
        "language_set": "भाषा {label} सेट कर दी गई है।",
        "yes": "हाँ",
        "no": "नहीं",
    },
    "kn-IN": {
        "reply_with_number": "ದಯವಿಟ್ಟು ಸಂಖ್ಯೆಯನ್ನು ಉತ್ತರವಾಗಿ ಕಳುಹಿಸಿ:",
        "select_language": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ:",
        "helpful_prompt": "ಈ ಉತ್ತರ ಸಹಾಯಕವಾಗಿತ್ತೇ?",
        "feedback_reason_prompt": "ದಯವಿಟ್ಟು ಕಾರಣವನ್ನು ಆಯ್ಕೆಮಾಡಿ (ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ):",
        "feedback_thanks": "ಧನ್ಯವಾದಗಳು. ನೀವು ಮುಂದಿನ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಬಹುದು.",
        "end_session": "0. ಸೆಷನ್ ಮುಗಿಸಿ",
        "session_ended": "ಸೆಷನ್ ಮುಗಿಸಲಾಗಿದೆ. ಹೊಸ ಚಾಟ್ ಆರಂಭಿಸಲು ಹೊಸ ಸಂದೇಶ ಕಳುಹಿಸಿ.",
        "language_set": "ಭಾಷೆ {label} ಎಂದು ಹೊಂದಿಸಲಾಗಿದೆ.",
        "yes": "ಹೌದು",
        "no": "ಇಲ್ಲ",
    },
    "ta-IN": {
        "reply_with_number": "எண்ணை பதிலாக அனுப்பவும்:",
        "select_language": "தயவு செய்து உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்:",
        "helpful_prompt": "இந்த பதில் பயனுள்ளதாக இருந்ததா?",
        "feedback_reason_prompt": "தயவு செய்து காரணத்தை பகிரவும் (எண்ணை அனுப்பவும்):",
        "feedback_thanks": "நன்றி. உங்கள் அடுத்த கேள்வியை கேட்கலாம்.",
        "end_session": "0. அமர்வை முடிக்கவும்",
        "session_ended": "அமர்வு முடிக்கப்பட்டது. புதிய உரையாடலுக்கு புதிய செய்தி அனுப்பவும்.",
        "language_set": "மொழி {label} ஆக அமைக்கப்பட்டது.",
        "yes": "ஆம்",
        "no": "இல்லை",
    },
    "te-IN": {
        "reply_with_number": "దయచేసి నంబర్‌తో జవాబు ఇవ్వండి:",
        "select_language": "దయచేసి మీ భాషను ఎంచుకోండి:",
        "helpful_prompt": "ఈ సమాధానం ఉపయోగకరంగా ఉందా?",
        "feedback_reason_prompt": "దయచేసి కారణం చెప్పండి (నంబర్‌తో జవాబు ఇవ్వండి):",
        "feedback_thanks": "ధన్యవాదాలు. మీరు తదుపరి ప్రశ్న అడగవచ్చు.",
        "end_session": "0. సెషన్ ముగించండి",
        "session_ended": "సెషన్ ముగించబడింది. కొత్త చాట్ కోసం కొత్త సందేశం పంపండి.",
        "language_set": "భాష {label}గా సెట్ అయింది.",
        "yes": "అవును",
        "no": "కాదు",
    },
    "ml-IN": {
        "reply_with_number": "ദയവായി നമ്പർ ആയി മറുപടി നൽകുക:",
        "select_language": "ദയവായി നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കൂ:",
        "helpful_prompt": "ഈ മറുപടി സഹായകരമായിരുന്നോ?",
        "feedback_reason_prompt": "ദയവായി കാരണം പങ്കിടൂ (നമ്പർ ആയി മറുപടി നൽകൂ):",
        "feedback_thanks": "നന്ദി. നിങ്ങൾക്ക് അടുത്ത ചോദ്യം ചോദിക്കാം.",
        "end_session": "0. സെഷൻ അവസാനിപ്പിക്കുക",
        "session_ended": "സെഷൻ അവസാനിപ്പിച്ചു. പുതിയ ചാറ്റിനായി പുതിയ സന്ദേശം അയക്കൂ.",
        "language_set": "ഭാഷ {label} ആയി സജ്ജമാക്കി.",
        "yes": "അതെ",
        "no": "ഇല്ല",
    },
}

_LOCALIZED_LANGUAGE_LABELS: dict[str, dict[str, str]] = {
    "en-IN": {"en-IN": "English", "hi-IN": "Hindi", "ta-IN": "Tamil", "te-IN": "Telugu", "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "gu-IN": "Gujarati", "bn-IN": "Bengali", "ur-IN": "Urdu"},
    "hi-IN": {"en-IN": "अंग्रेज़ी", "hi-IN": "हिंदी", "ta-IN": "तमिल", "te-IN": "तेलुगु", "kn-IN": "कन्नड़", "ml-IN": "मलयालम", "mr-IN": "मराठी", "gu-IN": "गुजराती", "bn-IN": "बांग्ला", "ur-IN": "उर्दू"},
    "kn-IN": {"en-IN": "ಇಂಗ್ಲಿಷ್", "hi-IN": "ಹಿಂದಿ", "ta-IN": "ತಮಿಳು", "te-IN": "ತೆಲುಗು", "kn-IN": "ಕನ್ನಡ", "ml-IN": "ಮಲಯಾಳಂ", "mr-IN": "ಮರಾಠಿ", "gu-IN": "ಗುಜರಾತಿ", "bn-IN": "ಬೆಂಗಾಳಿ", "ur-IN": "ಉರ್ದು"},
}


def _session_language(session_id: str) -> str:
    return orchestrator.session_language_memory.get(session_id, "en-IN")


def _ui_text(session_id: str, key: str, language_code: str | None = None) -> str:
    lang = language_code or _session_language(session_id)
    return _UI_STRINGS.get(lang, _UI_STRINGS["en-IN"]).get(key, _UI_STRINGS["en-IN"].get(key, key))


def _localize_text(session_id: str, text: str, language_code: str | None = None) -> str:
    target_language = language_code or _session_language(session_id)
    if target_language == "en-IN":
        return text
    translated = sarvam.translate_response_text(
        text=text,
        source_language=None,
        target_language=target_language,
        conversation_id=session_id,
        channel="whatsapp",
    )
    return translated.get("text", text)


def _is_end_session_command(user_input: str) -> bool:
    text = (user_input or "").strip().lower()
    return text in {"0", "end", "end session", "restart", "new chat", "reset"}


def _clear_session_state(session_id: str) -> None:
    _pending_follow_up_options.pop(session_id, None)
    _pending_language_selection.pop(session_id, None)
    _pending_initial_message.pop(session_id, None)
    _pending_feedback.pop(session_id, None)
    _pending_pincode_input.pop(session_id, None)
    _session_reply_audio_enabled.pop(session_id, None)

    orchestrator.session_language_memory.pop(session_id, None)
    orchestrator.session_history.pop(session_id, None)
    orchestrator.session_last_results.pop(session_id, None)
    orchestrator.session_profiles.pop(session_id, None)
    if session_id in orchestrator.session_welcome_sent:
        orchestrator.session_welcome_sent.remove(session_id)


def _with_end_session_option(session_id: str, text: str) -> str:
    base = (text or "").strip()
    marker = _ui_text(session_id, "end_session")
    if marker in base:
        return base
    if not base:
        return marker
    return f"{base}\n\n{marker}"


def _chunk_message(text: str, limit: int = _TWILIO_MESSAGE_CHAR_LIMIT) -> list[str]:
    content = (text or "").strip()
    if not content:
        return [""]
    if len(content) <= limit:
        return [content]

    chunks: list[str] = []
    current = ""
    for line in content.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = line
        else:
            # Single long line: hard split.
            start = 0
            while start < len(line):
                part = line[start:start + limit]
                chunks.append(part)
                start += limit
            current = ""
    if current:
        chunks.append(current)
    return chunks or [content[:limit]]


def _map_whatsapp_selection(session_id: str, user_input: str) -> str:
    options = _pending_follow_up_options.get(session_id, [])
    if not options:
        return user_input

    text = (user_input or "").strip()
    if not text:
        return text

    # Numeric selection: "1", "2", ...
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            selected = options[idx].get("value", text)
            _pending_follow_up_options.pop(session_id, None)
            return selected

    lowered = text.lower()
    for option in options:
        value = (option.get("value") or "").strip()
        label = (option.get("label") or "").strip()
        if lowered == value.lower() or lowered == label.lower():
            _pending_follow_up_options.pop(session_id, None)
            return value or text

    return text


def _format_whatsapp_reply(session_id: str, answer: str, follow_up_options: list[dict[str, str]]) -> str:
    if not follow_up_options:
        return answer

    lang = _session_language(session_id)
    lines = [answer.strip(), "", _ui_text(session_id, "reply_with_number", language_code=lang)]
    for idx, option in enumerate(follow_up_options, start=1):
        label = option.get("label") or option.get("value") or str(idx)
        lines.append(f"{idx}. {label}")
    return "\n".join(lines).strip()


def _format_language_menu(session_id: str) -> str:
    lang = _session_language(session_id)
    lines = [_ui_text(session_id, "select_language", language_code=lang), "", _ui_text(session_id, "reply_with_number", language_code=lang)]
    labels = _LOCALIZED_LANGUAGE_LABELS.get(lang, _LOCALIZED_LANGUAGE_LABELS["en-IN"])
    for idx, item in enumerate(_LANGUAGE_CHOICES, start=1):
        lines.append(f"{idx}. {labels.get(item['value'], item['label'])}")
    return "\n".join(lines).strip()


def _resolve_language_selection(user_input: str) -> str | None:
    text = (user_input or "").strip()
    if not text:
        return None
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(_LANGUAGE_CHOICES):
            return _LANGUAGE_CHOICES[idx]["value"]
        return None

    lowered = text.lower()
    for item in _LANGUAGE_CHOICES:
        if lowered == item["value"].lower() or lowered == item["label"].lower():
            return item["value"]
    return None


def _feedback_prompt(session_id: str, language_code: str) -> str:
    lines = [
        _ui_text(session_id, "helpful_prompt", language_code=language_code),
        _ui_text(session_id, "reply_with_number", language_code=language_code),
        f"1. {_ui_text(session_id, 'yes', language_code=language_code)}",
        f"2. {_ui_text(session_id, 'no', language_code=language_code)}",
    ]
    return "\n".join(lines)


def _feedback_thanks(session_id: str, language_code: str) -> str:
    return _ui_text(session_id, "feedback_thanks", language_code=language_code)


def _feedback_reason_prompt(session_id: str, language_code: str) -> str:
    lines = [_ui_text(session_id, "feedback_reason_prompt", language_code=language_code)]
    for idx, item in enumerate(_FEEDBACK_REASON_CHOICES, start=1):
        lines.append(f"{idx}. {item['label']}")
    return _localize_text(session_id, "\n".join(lines), language_code=language_code)


def _should_offer_feedback(response: dict) -> bool:
    if response.get("follow_up_options"):
        return False
    actions = response.get("actions") or []
    if "profiling" in actions:
        return False
    return bool((response.get("answer") or "").strip())


def _resolve_feedback_reason(user_input: str) -> str:
    text = (user_input or "").strip()
    if not text:
        return ""
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(_FEEDBACK_REASON_CHOICES):
            return _FEEDBACK_REASON_CHOICES[idx]["label"]
    lowered = text.lower()
    for item in _FEEDBACK_REASON_CHOICES:
        if lowered in (item["value"].lower(), item["label"].lower()):
            return item["label"]
    return text


def _maybe_handle_feedback_input(session_id: str, incoming_message: str) -> str | None:
    ctx = _pending_feedback.get(session_id)
    if not ctx:
        return None

    text = (incoming_message or "").strip()
    language_code = str(ctx.get("language_code") or "en-IN")
    stage = str(ctx.get("stage") or "helpful")

    yes_inputs = {"1", "yes", "y", "haan", "ha", "helpful", "useful"}
    no_inputs = {"2", "no", "n", "nah", "not helpful"}

    if stage == "helpful":
        lowered = text.lower()
        if lowered in yes_inputs:
            _pending_feedback.pop(session_id, None)
            return _feedback_thanks(session_id, language_code)
        if lowered in no_inputs:
            ctx["stage"] = "reason"
            _pending_feedback[session_id] = ctx
            return _feedback_reason_prompt(session_id, language_code)
        # Treat non-feedback text as a new user query.
        _pending_feedback.pop(session_id, None)
        return None

    # stage == reason
    reason = _resolve_feedback_reason(text)
    if not reason:
        return _feedback_reason_prompt(session_id, language_code)

    question = str(ctx.get("question") or "")
    original_answer = str(ctx.get("answer") or "")
    location = ctx.get("location") if isinstance(ctx.get("location"), dict) else {}
    sources = ctx.get("sources") if isinstance(ctx.get("sources"), list) else []
    improved = orchestrator.retry(
        question=question,
        original_answer=original_answer,
        reason=reason,
        sources=sources,
        location={
            "state": str(location.get("state") or "Unknown"),
            "district": str(location.get("district") or "Unknown"),
        },
        language_code=language_code,
    )
    improved_localized = _localize_text(session_id, improved, language_code=language_code)
    _pending_feedback.pop(session_id, None)
    return f"{improved_localized}\n\n{_feedback_thanks(session_id, language_code)}"


def _answer_for_whatsapp(session_id: str, incoming_message: str, language_code: str | None = None) -> str:
    mapped_message = _map_whatsapp_selection(session_id=session_id, user_input=incoming_message)

    if mapped_message == "I will type my pincode":
        _pending_pincode_input[session_id] = True
        _pending_follow_up_options.pop(session_id, None)
        lang = language_code or _session_language(session_id)
        return _localize_text(session_id, "Please type your 6-digit pincode:", language_code=lang)

    response = orchestrator.answer(
        message=mapped_message,
        session_id=session_id,
        channel="whatsapp",
        language_code=language_code,
        location_hint=None,
    )
    options = response.get("follow_up_options") or []
    if options:
        _pending_follow_up_options[session_id] = options
    else:
        _pending_follow_up_options.pop(session_id, None)
    reply = _format_whatsapp_reply(session_id, response["answer"], options)
    if _should_offer_feedback(response):
        session_language = str(response.get("session_language") or response.get("language_code") or "en-IN")
        _pending_feedback[session_id] = {
            "stage": "helpful",
            "question": mapped_message,
            "answer": str(response.get("answer") or ""),
            "language_code": session_language,
            "location": response.get("location") or {},
            "sources": response.get("sources") or [],
        }
        reply = f"{reply}\n\n{_feedback_prompt(session_id, session_language)}"
    else:
        _pending_feedback.pop(session_id, None)
    return reply


def _handle_whatsapp_user_input(session_id: str, incoming_message: str) -> str:
    if _is_end_session_command(incoming_message):
        language_before_clear = _session_language(session_id)
        _clear_session_state(session_id)
        return _localize_text(
            session_id,
            "Session ended. You can start a fresh chat anytime by sending a new message.",
            language_code=language_before_clear,
        )

    feedback_reply = _maybe_handle_feedback_input(session_id=session_id, incoming_message=incoming_message)
    if feedback_reply is not None:
        return feedback_reply

    if _pending_pincode_input.get(session_id):
        import re
        if re.search(r"\b\d{6}\b", incoming_message):
            _pending_pincode_input.pop(session_id, None)
            return _answer_for_whatsapp(session_id=session_id, incoming_message=incoming_message)
        lang = _session_language(session_id)
        return _localize_text(session_id, "Please enter a valid 6-digit pincode:", language_code=lang)

    # First-touch language menu for better guided onboarding.
    if _pending_language_selection.get(session_id):
        chosen = _resolve_language_selection(incoming_message)
        if not chosen:
            return _format_language_menu(session_id)

        _pending_language_selection.pop(session_id, None)
        buffered = _pending_initial_message.pop(session_id, "").strip()
        first_message = buffered or "hi"
        language_label = _LOCALIZED_LANGUAGE_LABELS.get(chosen, _LOCALIZED_LANGUAGE_LABELS["en-IN"]).get(chosen, chosen)
        reply = _answer_for_whatsapp(session_id=session_id, incoming_message=first_message, language_code=chosen)
        prefix = _ui_text(session_id, "language_set", language_code=chosen).format(label=language_label)
        return f"{prefix}\n\n{reply}"

    if session_id not in orchestrator.session_language_memory:
        _pending_language_selection[session_id] = True
        _pending_initial_message[session_id] = incoming_message
        _pending_follow_up_options.pop(session_id, None)
        _pending_feedback.pop(session_id, None)
        return _format_language_menu(session_id)

    return _answer_for_whatsapp(session_id=session_id, incoming_message=incoming_message)


def _cleanup_old_audio_files() -> None:
    cutoff = time.time() - _AUDIO_TTL_SECONDS
    try:
        for audio_file in _PUBLIC_AUDIO_DIR.glob("*"):
            if audio_file.stat().st_mtime < cutoff:
                audio_file.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("audio_cleanup_failed err=%s", str(exc))


def _resolve_public_base_url(request: Request) -> str:
    settings = get_settings()
    configured = (settings.base_url or "").rstrip("/")
    if configured:
        return configured

    forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    forwarded_host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.url.netloc
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return ""


def _detect_audio_extension(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"RIFF"):
        return "wav"
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "mp3"
    if audio_bytes.startswith(b"OggS"):
        return "ogg"
    if audio_bytes.startswith(b"fLaC"):
        return "flac"
    return "bin"


def _store_audio_and_url(audio_base64: str, request: Request, audio_extension: str | None = None) -> str | None:
    """Decode base64 audio, write it to public storage, and return a Twilio-fetchable URL."""
    base_url = _resolve_public_base_url(request)
    if not base_url:
        logger.warning("audio_url_generation_skipped reason=missing_base_url")
        return None
    try:
        audio_bytes = base64.b64decode(audio_base64)
        _cleanup_old_audio_files()
        extension = (audio_extension or "").strip(".").lower() or _detect_audio_extension(audio_bytes)
        filename = f"{int(time.time() * 1000)}-{_uuid.uuid4().hex}.{extension}"
        file_path = _PUBLIC_AUDIO_DIR / filename
        file_path.write_bytes(audio_bytes)
        audio_url = f"{base_url}/public/audio/{filename}"
        logger.info("audio_url_generated url=%s extension=%s size_bytes=%s", audio_url, extension, len(audio_bytes))
        return audio_url
    except Exception as exc:
        logger.warning("audio_store_failed err=%s", str(exc))
        return None


def _remember_response_mode(session_id: str, started_with_audio: bool) -> None:
    _session_reply_audio_enabled.setdefault(session_id, started_with_audio)


def _should_send_audio_reply(session_id: str) -> bool:
    return _session_reply_audio_enabled.get(session_id, False)


@router.post("/webhook")
def webhook(payload: WhatsAppWebhookRequest):
    """Demo JSON endpoint used by the web UI simulation."""
    _remember_response_mode(payload.from_number, started_with_audio=False)
    reply_text = _handle_whatsapp_user_input(
        session_id=payload.from_number,
        incoming_message=payload.message,
    )
    reply_text = _with_end_session_option(payload.from_number, reply_text)
    session_language = orchestrator.session_language_memory.get(payload.from_number, "en-IN")
    if _should_send_audio_reply(payload.from_number) and reply_text:
        tts = sarvam.text_to_speech(reply_text, session_language)
    else:
        tts = {
            "status": "skipped",
            "detail": "Audio reply disabled for text-started session",
            "audio_base64": None,
            "audio_mime_type": None,
            "audio_extension": None,
        }
    return {
        "to": payload.from_number,
        "channel": "whatsapp-mock",
        "reply": reply_text,
        "audio_status": tts.get("status"),
        "audio_detail": tts.get("detail"),
        "audio_base64": tts.get("audio_base64"),
        "audio_mime_type": tts.get("audio_mime_type"),
        "meta": {
            "detected_language": session_language,
            "pending_language_selection": _pending_language_selection.get(payload.from_number, False),
            "pending_follow_up_options": len(_pending_follow_up_options.get(payload.from_number, [])),
        },
    }


@router.post("/twilio", response_class=PlainTextResponse)
async def twilio_webhook(request: Request):
    """
    Real Twilio WhatsApp webhook.
    Configure this URL in Twilio Console → Messaging → Sandbox settings.
    Twilio sends form-encoded POST data; we reply with TwiML XML.
    """
    settings = get_settings()

    form = await request.form()
    from_number: str = form.get("From", "")
    body: str = form.get("Body", "")
    message_sid: str = form.get("MessageSid", "")
    media_count_raw: str = form.get("NumMedia", "0")
    media_content_type_0: str = form.get("MediaContentType0", "")
    media_url_0: str = form.get("MediaUrl0", "")

    if not from_number:
        raise HTTPException(status_code=400, detail="Missing From field")

    # Validate Twilio signature in production only.
    # Skipped in DEBUG mode because behind ngrok the request URL seen by the
    # server is http://localhost:8000/... while Twilio signs the public ngrok URL.
    if settings.twilio_account_sid and settings.twilio_auth_token and not settings.debug:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.twilio_auth_token)
            signature = request.headers.get("X-Twilio-Signature", "")
            # Reconstruct the public URL using forwarded headers (set by ngrok/proxy)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
            forwarded_host = request.headers.get("X-Forwarded-Host", request.url.netloc)
            public_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
            params = dict(form)
            if not validator.validate(public_url, params, signature):
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        except ImportError:
            pass  # twilio not installed, skip validation

    try:
        media_count = int(media_count_raw or "0")
    except ValueError:
        media_count = 0

    incoming_message = (body or "").strip()
    started_with_audio = media_count > 0 and media_content_type_0.startswith("audio/")
    _remember_response_mode(from_number, started_with_audio=started_with_audio)
    logger.info(
        "whatsapp_session_mode from=%s session_audio_enabled=%s inbound_audio=%s message_sid=%s",
        from_number,
        _should_send_audio_reply(from_number),
        started_with_audio,
        message_sid or "-",
    )

    # Twilio WhatsApp voice notes are sent as media with empty Body.
    if started_with_audio:
        # Pass current session language (or None = auto-detect) to Sarvam STT.
        session_lang = orchestrator.session_language_memory.get(from_number)
        stt = sarvam.transcribe_audio_url(
            media_url=media_url_0,
            mime_type=media_content_type_0 or "audio/ogg",
            auth_username=settings.twilio_account_sid,
            auth_password=settings.twilio_auth_token,
            language_code=session_lang,
        )
        transcript = (stt.get("transcript") or "").strip()
        detected_lang = stt.get("language_code")

        # If Sarvam detected a language and session has none yet, set it — skips language menu.
        if detected_lang and from_number not in orchestrator.session_language_memory:
            orchestrator.session_language_memory[from_number] = detected_lang
            _pending_language_selection.pop(from_number, None)
            _pending_initial_message.pop(from_number, None)

        if transcript:
            reply_text = _handle_whatsapp_user_input(session_id=from_number, incoming_message=transcript)
        elif incoming_message:
            reply_text = _handle_whatsapp_user_input(session_id=from_number, incoming_message=incoming_message)
        else:
            reply_text = _localize_text(
                from_number,
                "I received your voice note but could not transcribe it. Please resend audio clearly or send text.",
                language_code=session_lang,
            )
            _clear_session_state(from_number)
    elif not incoming_message:
        reply_text = "Please send a text message so I can help you."
        _clear_session_state(from_number)
    else:
        reply_text = _handle_whatsapp_user_input(session_id=from_number, incoming_message=incoming_message)

    reply_text = _with_end_session_option(from_number, reply_text)

    parts = _chunk_message(reply_text)

    # Generate TTS audio for the first chunk (skip menu/numbered lists — they don't read well).
    audio_url: str | None = None
    first_part = parts[0] if parts else ""
    is_menu = any(line.strip().startswith(("1.", "2.", "3.")) for line in first_part.splitlines())
    if first_part and not is_menu and _should_send_audio_reply(from_number):
        session_lang = orchestrator.session_language_memory.get(from_number, "en-IN")
        tts = sarvam.text_to_speech(text=first_part, language_code=session_lang)
        if tts.get("status") == "ok" and tts.get("audio_base64"):
            audio_url = _store_audio_and_url(
                tts["audio_base64"],
                request,
                audio_extension=tts.get("audio_extension"),
            )
        else:
            logger.warning(
                "whatsapp_tts_unavailable from=%s status=%s detail=%s",
                from_number,
                tts.get("status"),
                tts.get("detail"),
            )
    elif _should_send_audio_reply(from_number):
        logger.info(
            "whatsapp_audio_reply_skipped from=%s first_part_present=%s is_menu=%s",
            from_number,
            bool(first_part),
            is_menu,
        )

    messages_xml = ""
    for idx, part in enumerate(parts):
        if part is None:
            continue
        if idx == 0 and audio_url:
            messages_xml += f"<Message><Body>{escape(part)}</Body><Media>{escape(audio_url)}</Media></Message>"
        else:
            messages_xml += f"<Message>{escape(part)}</Message>"

    twiml = f"<?xml version='1.0' encoding='UTF-8'?><Response>{messages_xml}</Response>"
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.get("/twilio")
def twilio_webhook_status():
    return {
        "status": "ok",
        "endpoint": "/whatsapp/twilio",
        "method": "POST",
        "message": "This endpoint is active. Twilio should send POST webhooks here.",
    }
