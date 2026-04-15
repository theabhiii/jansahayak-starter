from __future__ import annotations

import logging
import re
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
    MAX_HISTORY_TURNS = 6

    def __init__(self) -> None:
        self.settings = get_settings()
        self.kb = KnowledgeBase()
        self.feedback = FeedbackService()
        self.sarvam = SarvamService()
        self.session_language_memory: dict[str, str] = {}
        self.session_history: dict[str, list[dict[str, str]]] = {}
        self.session_last_results: dict[str, list[dict[str, str]]] = {}

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
        history = self.session_history.get(session_id, [])
        last_results = self.session_last_results.get(session_id, [])
        contextual_query = self._build_contextual_query(message, history, last_results)

        location = resolve_location(
            text=contextual_query,
            location_hint=location_hint,
            default_state=self.settings.default_state,
            default_district=self.settings.default_district,
        )
        results = self.kb.search(contextual_query, state=location["state"], district=location["district"])
        self.session_last_results[session_id] = [
            {"id": r.get("id", ""), "title": r.get("title", "")}
            for r in results
        ]
        eligibility = check_eligibility(contextual_query, location["state"])
        grievance = route_grievance(contextual_query, location["state"], location["district"])
        sources = [{"id": r["id"], "title": r["title"], "url": r["source_url"]} for r in results]
        discovered_sources = self.kb.discover_sources(contextual_query, state=location["state"], limit=6)
        merged_sources: list[dict] = []
        seen_keys: set[str] = set()
        for src in sources + discovered_sources:
            url = src.get("url")
            title = src.get("title", "")
            key = f"{title}|{url}"
            if not url or key in seen_keys:
                continue
            seen_keys.add(key)
            merged_sources.append(src)
        if grievance.get("portal"):
            grievance_key = f"state-grievance-portal|{grievance['portal']}"
            if grievance_key not in seen_keys:
                seen_keys.add(grievance_key)
                merged_sources.append(
                    {"id": "state-grievance-portal", "title": f"{location['state']} Official Grievance/Services Portal", "url": grievance["portal"]}
                )
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
            chat_history=history,
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
        self._append_history(session_id, "user", message)
        self._append_history(session_id, "assistant", final_answer)

        return {
            "session_id": session_id,
            "session_language": session_language,
            "language_code": session_language,
            "detected_language": detection.language_code,
            "detection_confidence": round(float(detection.confidence), 3),
            "location": location,
            "answer": final_answer,
            "sources": merged_sources,
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

        local_count = sum(1 for r in results if r["states"] == ["All"] or location["state"] in r["states"])
        geo_note = (
            f"{local_count} of {len(results)} recommendations are mapped to {location['state']} "
            f"or available nationally."
        )
        bullets = [
            f"- {record['title']}: {record['benefits']} Eligibility: {record['eligibility']} Application: {record['application']}"
            for record in results
        ]
        return (
            f"Based on your location in {location['district']}, {location['state']}, here are the most relevant options:\n"
            + "\n".join(bullets)
            + f"\n\nGeo-specific coverage: {geo_note}"
            + f"\nEligibility check: {eligibility['reason']}"
            + f"\nGrievance routing: {grievance['department']} in {grievance['district']} ({grievance['portal']})."
        )

    def _append_history(self, session_id: str, role: str, content: str) -> None:
        entries = self.session_history.setdefault(session_id, [])
        entries.append({"role": role, "content": content})
        # keep recent window only
        if len(entries) > self.MAX_HISTORY_TURNS * 2:
            self.session_history[session_id] = entries[-(self.MAX_HISTORY_TURNS * 2):]

    def _build_contextual_query(
        self,
        message: str,
        history: list[dict[str, str]],
        last_results: list[dict[str, str]],
    ) -> str:
        if not history:
            return message
        # Include recent user intents so pronoun-based follow-ups are grounded.
        recent_user_context = [h["content"] for h in history if h.get("role") == "user"][-2:]
        parts: list[str] = []
        if recent_user_context:
            parts.extend(recent_user_context)

        lowered = message.lower()
        ordinal_map = {
            "first": 0,
            "1st": 0,
            "second": 1,
            "2nd": 1,
            "third": 2,
            "3rd": 2,
            "last": -1,
        }
        referenced_idx = None
        for token, idx in ordinal_map.items():
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                referenced_idx = idx
                break

        if referenced_idx is not None and last_results:
            if referenced_idx == -1:
                selected = last_results[-1]
            elif referenced_idx < len(last_results):
                selected = last_results[referenced_idx]
            else:
                selected = None
            if selected and selected.get("title"):
                parts.append(f"Referenced scheme: {selected['title']}")

        parts.append(message)
        return " | ".join(parts)

    def _language_error(self, language_code: str) -> str:
        if language_code == "hi-IN":
            return "à¤•à¥à¤·à¤®à¤¾ à¤•à¤°à¥‡à¤‚, à¤…à¤­à¥€ à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤­à¤¾à¤·à¤¾ à¤®à¥‡à¤‚ à¤‰à¤¤à¥à¤¤à¤° à¤¬à¤¨à¤¾à¤¨à¥‡ à¤®à¥‡à¤‚ à¤¸à¤®à¤¸à¥à¤¯à¤¾ à¤†à¤ˆà¥¤ à¤•à¥ƒà¤ªà¤¯à¤¾ à¤¦à¥‹à¤¬à¤¾à¤°à¤¾ à¤ªà¥à¤°à¤¯à¤¾à¤¸ à¤•à¤°à¥‡à¤‚à¥¤"
        if language_code == "es-ES":
            return "Lo siento, hubo un problema al generar la respuesta en el idioma solicitado. IntÃ©ntalo de nuevo."
        return "Sorry, there was a problem generating the response in the requested language. Please try again."
