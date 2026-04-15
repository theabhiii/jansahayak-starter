from __future__ import annotations

import logging
from uuid import uuid4

from ..core.config import get_settings
from ..utils.language import LanguageDetectionResult, detect_language, normalize_language_code
from ..utils.location import resolve_location
from .feedback_service import FeedbackService
from .knowledge_base import KnowledgeBase
from .mock_services import check_eligibility, route_grievance
from .sarvam_service import SarvamService

logger = logging.getLogger(__name__)


class Orchestrator:
    CLEAR_LANGUAGE_THRESHOLD = 0.62
    LOW_CONFIDENCE_THRESHOLD = 0.4

    def __init__(self) -> None:
        self.settings = get_settings()
        self.kb = KnowledgeBase()
        self.feedback = FeedbackService()
        self.sarvam = SarvamService()
        self.session_language_memory: dict[str, str] = {}

    def answer(
        self,
        message: str,
        session_id: str,
        channel: str = "web",
        language_code: str | None = None,
        location_hint: str | None = None,
    ) -> dict:
        detection = detect_language(message)
        session_language = self._resolve_session_language(session_id, detection, language_code)

        location = resolve_location(
            text=message,
            location_hint=location_hint,
            default_state=self.settings.default_state,
            default_district=self.settings.default_district,
        )
        results = self.kb.search(message, state=location["state"], district=location["district"])
        eligibility = check_eligibility(message, location["state"])
        grievance = route_grievance(message, location["state"], location["district"])
        sources = [{"id": r["id"], "title": r["title"], "url": r["source_url"]} for r in results]
        actions = ["scheme_discovery", "eligibility_check", "grievance_routing"]

        # Keep base content in English and always run a final translation layer.
        draft = self._answer_en(location, results, eligibility, grievance)

        ai_result = self.sarvam.generate_response(
            query=message,
            draft_answer=draft,
            detected_language=detection.language_code,
            response_language=session_language,
            conversation_id=session_id,
            channel=channel,
        )

        answer = ai_result["text"]
        received_language = normalize_language_code(ai_result.get("language")) or "en-IN"

        translated = self.sarvam.translate_response_text(
            text=answer,
            source_language=None,
            target_language=session_language,
            conversation_id=session_id,
            channel=channel,
        )
        final_answer = translated["text"]

        logger.info(
            "language_trace conversation_id=%s detected=%s sent=%s received=%s translated_target=%s confidence=%.3f",
            session_id,
            detection.language_code,
            session_language,
            received_language,
            translated["target_language"],
            detection.confidence,
        )

        mismatch_detected = translated.get("target_language", session_language) != session_language

        return {
            "session_id": session_id,
            "session_language": session_language,
            "language_code": session_language,
            "detected_language": detection.language_code,
            "detection_confidence": round(float(detection.confidence), 3),
            "location": location,
            "answer": final_answer,
            "sources": sources,
            "actions": actions,
            "feedback_token": str(uuid4()),
            "language_trace": {
                "detected_language": detection.language_code,
                "sent_response_language": session_language,
                "received_language": received_language,
                "mismatch_detected": mismatch_detected,
                "provider": ai_result.get("provider", "unknown"),
                "request_payload": ai_result.get("request_payload", {}),
                "translation_payload": translated.get("request_payload", {}),
                "translated_target_language": translated.get("target_language", session_language),
            },
        }

    def retry(self, question: str, original_answer: str, reason: str | None, sources: list, location: dict, language_code: str) -> str:
        return self.feedback.improve_answer(question, original_answer, reason, sources, location, language_code)

    def _resolve_session_language(
        self,
        session_id: str,
        detection: LanguageDetectionResult,
        user_requested_language: str | None,
    ) -> str:
        explicit = normalize_language_code(user_requested_language)
        if explicit:
            self.session_language_memory[session_id] = explicit
            return explicit

        existing = self.session_language_memory.get(session_id)
        detected = normalize_language_code(detection.language_code) or "en-IN"

        if not existing:
            self.session_language_memory[session_id] = detected
            return detected

        if detection.confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return existing

        if detected != existing and detection.confidence >= self.CLEAR_LANGUAGE_THRESHOLD:
            self.session_language_memory[session_id] = detected
            return detected

        return existing

    def _answer_en(self, location: dict, results: list, eligibility: dict, grievance: dict) -> str:
        if not results:
            return (
                f"I could not find a direct scheme match, so I am sharing a location-aware fallback for {location['district']}, {location['state']}. "
                "Please share whether you need a farmer, student, women entrepreneur, or grievance-related scheme."
            )

        bullets = [
            f"- {record['title']}: {record['benefits']} Eligibility: {record['eligibility']} Application: {record['application']}"
            for record in results
        ]
        return (
            f"Based on your location in {location['district']}, {location['state']}, here are the most relevant options:\n"
            + "\n".join(bullets)
            + f"\n\nEligibility check: {eligibility['reason']}"
            + f"\nGrievance routing: {grievance['department']} in {grievance['district']}."
        )

    def _language_error(self, language_code: str) -> str:
        if language_code == "hi-IN":
            return "क्षमा करें, अभी निर्धारित भाषा में उत्तर बनाने में समस्या आई। कृपया दोबारा प्रयास करें।"
        if language_code == "es-ES":
            return "Lo siento, hubo un problema al generar la respuesta en el idioma solicitado. Inténtalo de nuevo."
        return "Sorry, there was a problem generating the response in the requested language. Please try again."
