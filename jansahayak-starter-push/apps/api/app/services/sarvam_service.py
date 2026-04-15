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

        return {
            "text": draft_answer,
            "language": normalized_response,
            "provider": "mocked" if not self.is_configured() else "configured-fallback",
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

        payload = {
            "text": text,
            "source_language": normalized_source or "auto",
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
            source_language=normalized_source,
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

        # Preferred path: Sarvam SDK call as shared by user.
        if self._sdk_client is not None:
            try:
                resp = self._sdk_client.text.translate(
                    input=text,
                    source_language_code=source_language_code or "auto",
                    target_language_code=target_language_code,
                    speaker_gender=self.settings.sarvam_speaker_gender,
                    mode=self.settings.sarvam_translate_mode,
                    model=self.settings.sarvam_translate_model,
                    enable_preprocessing=self.settings.sarvam_enable_preprocessing,
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
                    source_language_code or "auto",
                    target_language_code,
                    str(exc),
                )

        # Backup path: direct REST call.
        if self.is_configured():
            try:
                headers = {
                    "api-subscription-key": self.settings.sarvam_api_key,
                    "Content-Type": "application/json",
                }
                body = {
                    "input": text,
                    "source_language_code": source_language_code or "auto",
                    "target_language_code": target_language_code,
                    "speaker_gender": self.settings.sarvam_speaker_gender,
                    "mode": self.settings.sarvam_translate_mode,
                    "model": self.settings.sarvam_translate_model,
                    "enable_preprocessing": self.settings.sarvam_enable_preprocessing,
                    "numerals_format": self.settings.sarvam_numerals_format,
                }
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(f"{self.settings.sarvam_base_url.rstrip('/')}/translate", headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    translated = data.get("translated_text")
                    if isinstance(translated, str) and translated.strip():
                        return translated
            except Exception as exc:
                logger.warning(
                    "sarvam_rest_translate_failed source=%s target=%s err=%s",
                    source_language_code or "auto",
                    target_language_code,
                    str(exc),
                )

        return self._fallback_translate(text, target_language_code)

    def _fallback_translate(self, text: str, target_language_code: str) -> str:
        if target_language_code == "hi-IN":
            replacements = {
                "Eligibility check": "Paatrata jaanch",
                "Grievance routing": "Shikayat routing",
                "Benefits": "Laabh",
                "Eligibility": "Paatrata",
                "Application": "Aavedan",
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

    def text_to_speech(self, text: str, language_code: str) -> dict:
        normalized_language = normalize_language_code(language_code) or "en-IN"
        if not self.is_configured():
            fake_audio = base64.b64encode(f"Demo audio for: {text}".encode("utf-8")).decode("utf-8")
            return {"status": "mocked", "detail": f"TTS fallback used for {normalized_language}", "audio_base64": fake_audio}
        return {"status": "todo", "detail": "Implement Sarvam TTS SDK call here", "audio_base64": None}

    def speech_to_text(self, transcript_hint: str | None = None, language_code: str | None = None) -> dict:
        normalized_language = normalize_language_code(language_code) or "en-IN"
        if not self.is_configured():
            return {
                "status": "mocked",
                "detail": "STT fallback used. Wire audio upload to Sarvam when key is available.",
                "transcript": transcript_hint or "",
                "language_code": normalized_language,
            }
        return {
            "status": "todo",
            "detail": "Implement Sarvam STT SDK call here",
            "transcript": transcript_hint or "",
            "language_code": normalized_language,
        }
