from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

from ..core.config import get_settings
from ..utils.language import normalize_language_code

try:
    from sarvamai import SarvamAI
except Exception:  # pragma: no cover - optional runtime dependency
    SarvamAI = None

logger = logging.getLogger(__name__)


class SarvamService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._sdk_client = None
        if self.is_configured() and SarvamAI is not None:
            try:
                self._sdk_client = SarvamAI(api_subscription_key=self.settings.sarvam_api_key)
            except Exception as exc:
                logger.warning("sarvam_sdk_init_failed err=%s", str(exc))

    def is_configured(self) -> bool:
        return bool(self.settings.sarvam_api_key)

    def _to_sravan_lang(self, language_code: str | None) -> str:
        normalized = normalize_language_code(language_code) or "en-IN"
        return normalized.split("-")[0]

    def _to_translate_language(self, language_code: str | None) -> str:
        normalized = normalize_language_code(language_code)
        mapping = {
            "en-IN": "english",
            "hi-IN": "hindi",
            "ta-IN": "tamil",
            "te-IN": "telugu",
            "kn-IN": "kannada",
            "ml-IN": "malayalam",
            "es-ES": "spanish",
        }
        if normalized in mapping:
            return mapping[normalized]
        return normalized or "english"

    def build_generation_payload(
        self,
        query: str,
        detected_language: str,
        response_language: str,
        conversation_id: str,
        channel: str,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "detected_language": self._to_sravan_lang(detected_language),
            "response_language": self._to_sravan_lang(response_language),
            "conversation_id": conversation_id,
            "channel": channel,
        }

    def generate_response(
        self,
        *,
        query: str,
        draft_answer: str,
        detected_language: str,
        response_language: str,
        conversation_id: str,
        channel: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        normalized_detected = normalize_language_code(detected_language) or "en-IN"
        normalized_response = normalize_language_code(response_language) or normalized_detected

        payload = self.build_generation_payload(
            query=query,
            detected_language=normalized_detected,
            response_language=normalized_response,
            conversation_id=conversation_id,
            channel=channel,
        )

        logger.info(
            "sravan_request conversation_id=%s detected=%s response=%s channel=%s",
            conversation_id,
            payload["detected_language"],
            payload["response_language"],
            channel,
        )

        if self.is_configured():
            try:
                headers = {
                    "Authorization": f"Bearer {self.settings.sarvam_api_key}",
                    "api-subscription-key": self.settings.sarvam_api_key,
                    "Content-Type": "application/json",
                }
                system_prompt = (
                    "You are a helpful multilingual citizen services assistant. "
                    f"Respond ONLY in language code {normalized_response}. "
                    "Keep responses concise and grounded in provided context. "
                    "Return only the final user-facing answer. "
                    "Never reveal internal reasoning, analysis, planning steps, or self-talk."
                )
                body = {
                    "model": self.settings.sarvam_chat_model,
                    "temperature": self.settings.sarvam_chat_temperature,
                    "messages": self._build_chat_messages(
                        system_prompt=system_prompt,
                        query=query,
                        detected_language=normalized_detected,
                        response_language=normalized_response,
                        draft_answer=draft_answer,
                        chat_history=chat_history or [],
                    ),
                }
                with httpx.Client(timeout=25.0) as client:
                    response = client.post(self.settings.sarvam_chat_url, headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    text = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content")
                    )
                    if isinstance(text, str) and text.strip():
                        cleaned_text = self._strip_meta_reasoning(text.strip())
                        return {
                            "text": cleaned_text,
                            "language": normalized_response,
                            "provider": "sarvam-chat",
                            "request_payload": payload,
                        }
                    logger.warning("sarvam_chat_empty_response conversation_id=%s", conversation_id)
            except Exception as exc:
                logger.warning("sarvam_chat_request_failed conversation_id=%s err=%s", conversation_id, str(exc))

        return {
            "text": self._strip_meta_reasoning(draft_answer),
            "language": normalized_response,
            "provider": "mocked" if not self.is_configured() else "configured-fallback",
            "request_payload": payload,
        }

    def _build_chat_messages(
        self,
        *,
        system_prompt: str,
        query: str,
        detected_language: str,
        response_language: str,
        draft_answer: str,
        chat_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in chat_history[-8:]:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Current query: {query}\n\n"
                    f"Detected language: {detected_language}\n"
                    f"Response language: {response_language}\n"
                    "Use the conversation history above for follow-up intent resolution.\n"
                    f"Grounding context for this turn:\n{draft_answer}"
                ),
            }
        )
        return messages

    def normalize_user_input(
        self,
        *,
        text: str,
        detected_language: str | None,
        conversation_id: str,
        channel: str,
    ) -> dict[str, Any]:
        normalized_detected = normalize_language_code(detected_language) or "en-IN"
        stripped = (text or "").strip()
        payload = {
            "text": stripped,
            "detected_language": normalized_detected,
            "target_language": "en-IN",
            "conversation_id": conversation_id,
            "channel": channel,
        }
        if not stripped:
            return {
                "text": stripped,
                "source_language": normalized_detected,
                "target_language": "en-IN",
                "translated": False,
                "provider": "noop-empty",
                "request_payload": payload,
            }
        if normalized_detected == "en-IN":
            return {
                "text": stripped,
                "source_language": normalized_detected,
                "target_language": "en-IN",
                "translated": False,
                "provider": "noop-english",
                "request_payload": payload,
            }

        logger.info(
            "sravan_input_translate_request conversation_id=%s detected=%s channel=%s",
            conversation_id,
            normalized_detected,
            channel,
        )

        translated = self.translate_text(
            text=stripped,
            target_language_code="en-IN",
            source_language=normalized_detected,
            force_translate=True,
        )
        translated_stripped = (translated or "").strip()
        if translated_stripped:
            return {
                "text": translated_stripped,
                "source_language": normalized_detected,
                "target_language": "en-IN",
                "translated": translated_stripped != stripped,
                "provider": "sarvam-translate-input",
                "request_payload": payload,
            }

        return {
            "text": stripped,
            "source_language": normalized_detected,
            "target_language": "en-IN",
            "translated": False,
            "provider": "input-translation-fallback",
            "request_payload": payload,
        }

    def translate_response_text(
        self,
        *,
        text: str,
        source_language: str | None,
        target_language: str,
        conversation_id: str,
        channel: str,
    ) -> dict[str, Any]:
        normalized_source = normalize_language_code(source_language)
        normalized_target = normalize_language_code(target_language) or "en-IN"

        resolved_source = normalized_source or normalize_language_code(self.settings.default_language) or "en-IN"

        if resolved_source == normalized_target:
            return {
                "text": text,
                "source_language": normalized_source,
                "target_language": normalized_target,
                "request_payload": {},
            }

        payload = {
            "text": text,
            "source_language": resolved_source,
            "target_language": normalized_target,
            "conversation_id": conversation_id,
            "channel": channel,
        }

        logger.info(
            "sravan_translation_request conversation_id=%s source=%s target=%s channel=%s",
            conversation_id,
            payload["source_language"],
            payload["target_language"],
            channel,
        )

        # Always run final-pass translation with source auto-detection
        # to normalize mixed-language content into the target language.
        translated = self.translate_text(
            text=text,
            target_language_code=normalized_target,
            source_language=resolved_source,
            force_translate=True,
        )

        return {
            "text": translated,
            "source_language": normalized_source,
            "target_language": normalized_target,
            "request_payload": payload,
        }

    def translate(self, text: str, target_language_code: str) -> str:
        return self.translate_text(text=text, target_language_code=target_language_code, source_language=None, force_translate=False)

    def translate_text(
        self,
        text: str,
        target_language_code: str,
        source_language: str | None = None,
        force_translate: bool = False,
    ) -> str:
        language_code = normalize_language_code(target_language_code) or "en-IN"
        source_code = normalize_language_code(source_language)
        if not force_translate and source_code and source_code == language_code:
            return text

        chunks = self._chunk_text(text, self._max_chunk_chars())
        translated_chunks = [self._translate_chunk(chunk, source_code, language_code) for chunk in chunks]
        return "\n".join(translated_chunks)

    def _max_chunk_chars(self) -> int:
        # Official docs note mayura:v1 has lower max input length than sarvam-translate:v1.
        model = (self.settings.sarvam_translate_model or "").lower()
        if model.startswith("mayura"):
            return 900
        return 1800

    def _chunk_text(self, text: str, max_chars: int = 1800) -> list[str]:
        stripped = (text or "").strip()
        if not stripped:
            return [""]
        paragraphs = re.split(r"(\n\s*\n)", stripped)
        chunks: list[str] = []
        current = ""

        for part in paragraphs:
            if len(current) + len(part) <= max_chars:
                current += part
                continue

            if current.strip():
                chunks.append(current.strip())

            if len(part) <= max_chars:
                current = part
            else:
                for i in range(0, len(part), max_chars):
                    piece = part[i:i + max_chars].strip()
                    if piece:
                        chunks.append(piece)
                current = ""

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [stripped]

    def _translate_chunk(self, text: str, source_language_code: str | None, target_language_code: str) -> str:
        if not text:
            return text
        resolved_source_code = normalize_language_code(source_language_code) or normalize_language_code(self.settings.default_language) or "en-IN"
        resolved_target_code = normalize_language_code(target_language_code) or "en-IN"

        if resolved_source_code == resolved_target_code:
            return text

        # Preferred path: Sarvam SDK call as shared by user.
        if self._sdk_client is not None:
            try:
                sdk_source_code = normalize_language_code(source_language_code) or "auto"
                resp = self._sdk_client.text.translate(
                    input=text,
                    source_language_code=sdk_source_code,
                    target_language_code=resolved_target_code,
                    speaker_gender=self.settings.sarvam_speaker_gender,
                    mode=self.settings.sarvam_translate_mode,
                    model=self.settings.sarvam_translate_model,
                    numerals_format=self.settings.sarvam_numerals_format,
                )

                translated_text = None
                if isinstance(resp, dict):
                    translated_text = resp.get("translated_text")
                else:
                    translated_text = getattr(resp, "translated_text", None)
                    if translated_text is None and hasattr(resp, "model_dump"):
                        translated_text = resp.model_dump().get("translated_text")

                if isinstance(translated_text, str) and translated_text.strip():
                    return translated_text
            except Exception as exc:
                logger.warning(
                    "sarvam_sdk_translate_failed source=%s target=%s err=%s",
                    resolved_source_code,
                    resolved_target_code,
                    str(exc),
                )

        # Primary REST path aligned with sample implementation:
        # POST https://api.sarvam.ai/translate/text
        # Authorization: Bearer <API_KEY>
        # Payload: { "text": "...", "target_language": "hindi" }
        if self.is_configured():
            try:
                headers = {
                    "Authorization": f"Bearer {self.settings.sarvam_api_key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "input": text,
                    "source_language_code": resolved_source_code,
                    "target_language_code": resolved_target_code,
                    "speaker_gender": self.settings.sarvam_speaker_gender,
                    "mode": self.settings.sarvam_translate_mode,
                    "model": self.settings.sarvam_translate_model,
                    "enable_preprocessing": self.settings.sarvam_enable_preprocessing,
                    "numerals_format": self.settings.sarvam_numerals_format,
                }
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(self.settings.sarvam_translate_url, headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    translated = data.get("translated_text") or data.get("translation")
                    if isinstance(translated, str) and translated.strip():
                        return translated
            except Exception as exc:
                logger.warning(
                    "sarvam_translate_text_failed source=%s target=%s err=%s",
                    resolved_source_code,
                    resolved_target_code,
                    str(exc),
                )

        return self._fallback_translate(text, resolved_target_code)

    def _fallback_translate(self, text: str, target_language_code: str) -> str:
        if target_language_code == "hi-IN":
            replacements = {
                "Based on your location in": "आपके स्थान ",
                ", here are the most relevant options:": " के आधार पर सबसे उपयुक्त विकल्प ये हैं:",
                "Geo-specific coverage:": "भौगोलिक कवरेज:",
                "recommendations are mapped to": "सुझाव",
                "or available nationally.": "या राष्ट्रीय स्तर पर उपलब्ध हैं।",
                "Eligibility check:": "पात्रता जांच:",
                "Grievance routing:": "शिकायत मार्गदर्शन:",
                "I could not find a direct scheme match, so I am sharing a location-aware fallback for": "सीधा योजना मिलान नहीं मिला, इसलिए मैं स्थान-आधारित सुझाव साझा कर रहा/रही हूँ:",
                "Please share whether you need a farmer, student, women entrepreneur, or grievance-related scheme.": "कृपया बताएं कि आपको किसान, छात्र, महिला उद्यमी या शिकायत से जुड़ी योजना चाहिए।",
                "Eligibility check": "Paatrata jaanch",
                "Grievance routing": "Shikayat routing",
                "Benefits": "लाभ",
                "Eligibility": "पात्रता",
                "Application": "आवेदन",
                "Residents of": "निवासी",
                "Citizens": "नागरिक",
                "Submit": "जमा करें",
                "Apply through": "इसके माध्यम से आवेदन करें",
                "in instalments.": "किस्तों में।",
            }
            translated = text
            for src, dst in replacements.items():
                translated = translated.replace(src, dst)
            return translated

        if target_language_code == "es-ES":
            replacements = {
                "Eligibility check": "Verificacion de elegibilidad",
                "Grievance routing": "Ruta de queja",
                "Benefits": "Beneficios",
                "Eligibility": "Elegibilidad",
                "Application": "Solicitud",
            }
            translated = text
            for src, dst in replacements.items():
                translated = translated.replace(src, dst)
            return translated

        return text

    def _strip_meta_reasoning(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return raw

        # If model adds meta preface before the real answer, keep the useful part.
        anchors = [
            "here are",
            "based on your location",
            "निम्नलिखित",
            "यहाँ",
            "ये विकल्प",
            "options:",
            "उत्तर:",
        ]
        lowered = raw.lower()
        cut_idx = None
        for anchor in anchors:
            idx = lowered.find(anchor.lower())
            if idx > 0:
                cut_idx = idx if cut_idx is None else min(cut_idx, idx)
        if cut_idx is not None:
            prefix = lowered[:cut_idx]
            if any(
                token in prefix
                for token in [
                    "let me",
                    "i need to",
                    "i should",
                    "thinking",
                    "analysis",
                    "विचार",
                    "मुझे",
                    "जाँच",
                    "चेक",
                ]
            ):
                raw = raw[cut_idx:].lstrip(" :-\n\t")

        lines = [ln.strip() for ln in raw.splitlines()]
        meta_tokens = [
            "let me",
            "i need to",
            "i should",
            "i will",
            "analysis",
            "thinking",
            "विचार",
            "मुझे",
            "जाँच",
            "check",
            "history",
        ]
        pruned: list[str] = []
        skipping = True
        for line in lines:
            if not line:
                if not skipping:
                    pruned.append(line)
                continue
            ll = line.lower()
            is_meta = any(tok in ll for tok in meta_tokens)
            if skipping and is_meta:
                continue
            skipping = False
            pruned.append(line)

        cleaned = "\n".join(pruned).strip()
        return cleaned or raw

    def transcribe_audio_bytes(
        self,
        *,
        audio_bytes: bytes,
        file_name: str = "audio.ogg",
        mime_type: str = "audio/ogg",
        language_code: str | None = None,
    ) -> dict[str, Any]:
        normalized_language = normalize_language_code(language_code) or "unknown"
        if not audio_bytes:
            return {
                "status": "error",
                "detail": "Empty audio payload",
                "transcript": "",
                "language_code": normalized_language if normalized_language != "unknown" else "en-IN",
                "provider": "none",
            }

        if self._sdk_client is not None:
            try:
                codec = self._content_type_to_codec(mime_type)
                file_tuple = (file_name, audio_bytes, mime_type)
                transcribe_kwargs: dict[str, Any] = {
                    "file": file_tuple,
                    "model": "saarika:v2.5",
                    "mode": "transcribe",
                    "input_audio_codec": codec,
                }
                if normalized_language and normalized_language != "unknown":
                    transcribe_kwargs["language_code"] = normalized_language
                resp = self._sdk_client.speech_to_text.transcribe(**transcribe_kwargs)

                transcript = ""
                resolved_language = normalize_language_code(language_code) or "en-IN"
                if isinstance(resp, dict):
                    transcript = (resp.get("transcript") or "").strip()
                    resolved_language = normalize_language_code(resp.get("language_code")) or resolved_language
                else:
                    transcript = (getattr(resp, "transcript", "") or "").strip()
                    resolved_language = normalize_language_code(getattr(resp, "language_code", None)) or resolved_language
                    if not transcript and hasattr(resp, "model_dump"):
                        data = resp.model_dump()
                        transcript = (data.get("transcript") or "").strip()
                        resolved_language = normalize_language_code(data.get("language_code")) or resolved_language

                if transcript:
                    return {
                        "status": "ok",
                        "detail": "Transcription successful",
                        "transcript": transcript,
                        "language_code": resolved_language,
                        "provider": "sarvam-stt-sdk",
                    }
            except Exception as exc:
                logger.warning("sarvam_stt_transcribe_failed err=%s", str(exc))

        return {
            "status": "mocked",
            "detail": "STT unavailable, returning empty transcript fallback.",
            "transcript": "",
            "language_code": normalize_language_code(language_code) or "en-IN",
            "provider": "stt-fallback",
        }

    def transcribe_audio_url(
        self,
        *,
        media_url: str,
        mime_type: str = "audio/ogg",
        auth_username: str | None = None,
        auth_password: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        if not media_url:
            return {
                "status": "error",
                "detail": "Missing media URL",
                "transcript": "",
                "language_code": normalize_language_code(language_code) or "en-IN",
                "provider": "none",
            }

        try:
            auth: tuple[str, str] | None = None
            if auth_username and auth_password:
                auth = (auth_username, auth_password)
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(media_url, auth=auth)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", mime_type) or mime_type
                file_name = self._guess_audio_filename(content_type)
                return self.transcribe_audio_bytes(
                    audio_bytes=response.content,
                    file_name=file_name,
                    mime_type=content_type,
                    language_code=language_code,
                )
        except Exception as exc:
            logger.warning("audio_download_failed url=%s err=%s", media_url, str(exc))
            return {
                "status": "error",
                "detail": "Failed to download audio from media URL",
                "transcript": "",
                "language_code": normalize_language_code(language_code) or "en-IN",
                "provider": "download-failed",
            }

    def text_to_speech(self, text: str, language_code: str) -> dict:
        normalized_language = normalize_language_code(language_code) or "en-IN"
        if not self.is_configured() or self._sdk_client is None:
            fake_audio = base64.b64encode(f"Demo audio for: {text}".encode("utf-8")).decode("utf-8")
            return {"status": "mocked", "detail": f"TTS fallback used for {normalized_language}", "audio_base64": fake_audio}
        try:
            resp = self._sdk_client.text_to_speech.convert(
                text=text[:2500],
                target_language_code=normalized_language,
                model="bulbul:v3",
                enable_preprocessing=self.settings.sarvam_enable_preprocessing,
            )
            audios = getattr(resp, "audios", None) or (resp.get("audios") if isinstance(resp, dict) else None) or []
            if audios:
                return {
                    "status": "ok",
                    "detail": "TTS successful",
                    "audio_base64": audios[0],
                    "language_code": normalized_language,
                    "provider": "sarvam-tts-sdk",
                }
        except Exception as exc:
            logger.warning("sarvam_tts_failed err=%s", str(exc))
        return {"status": "error", "detail": "TTS failed", "audio_base64": None, "language_code": normalized_language}

    def speech_to_text(
        self,
        transcript_hint: str | None = None,
        language_code: str | None = None,
        audio_base64: str | None = None,
        mime_type: str | None = None,
    ) -> dict:
        normalized_language = normalize_language_code(language_code) or "en-IN"
        if audio_base64:
            try:
                audio_bytes = base64.b64decode(audio_base64, validate=True)
                stt = self.transcribe_audio_bytes(
                    audio_bytes=audio_bytes,
                    file_name=self._guess_audio_filename(mime_type or "audio/ogg"),
                    mime_type=mime_type or "audio/ogg",
                    language_code=normalized_language,
                )
                if stt.get("transcript"):
                    return stt
            except Exception as exc:
                logger.warning("stt_audio_base64_decode_failed err=%s", str(exc))

        if transcript_hint:
            return {
                "status": "mocked",
                "detail": "Using transcript hint fallback.",
                "transcript": transcript_hint,
                "language_code": normalized_language,
                "provider": "transcript-hint",
            }

        return {
            "status": "mocked",
            "detail": "No transcript available. Provide audio_base64 or transcript_hint.",
            "transcript": "",
            "language_code": normalized_language,
            "provider": "stt-fallback",
        }

    def _content_type_to_codec(self, content_type: str) -> str:
        lowered = (content_type or "").lower()
        if "wav" in lowered:
            return "wav"
        if "mpeg" in lowered or "mp3" in lowered:
            return "mp3"
        if "aac" in lowered:
            return "aac"
        if "webm" in lowered:
            return "webm"
        if "m4a" in lowered or "mp4" in lowered:
            return "mp4"
        if "flac" in lowered:
            return "flac"
        if "opus" in lowered or "ogg" in lowered:
            return "ogg"
        return "ogg"

    def _guess_audio_filename(self, content_type: str) -> str:
        lowered = (content_type or "").lower()
        if "wav" in lowered:
            return "audio.wav"
        if "mpeg" in lowered or "mp3" in lowered:
            return "audio.mp3"
        if "aac" in lowered:
            return "audio.aac"
        if "webm" in lowered:
            return "audio.webm"
        if "m4a" in lowered or "mp4" in lowered:
            return "audio.m4a"
        if "flac" in lowered:
            return "audio.flac"
        if "opus" in lowered or "ogg" in lowered:
            return "audio.ogg"
        return "audio.bin"
