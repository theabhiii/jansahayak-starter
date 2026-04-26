from __future__ import annotations

import logging
import re
from typing import Any
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
    IN_SCOPE_KEYWORDS = {
        "scheme", "schemes", "yojana", "eligibility", "eligible", "apply", "application", "status",
        "grievance", "complaint", "benefit", "subsidy", "certificate", "ration", "pds",
        "citizen service", "government service", "kisan", "farmer", "student", "women entrepreneur",
        "location", "pincode", "district", "state",
        "योजना", "पात्रता", "आवेदन", "शिकायत", "लाभ", "किसान", "छात्र", "महिला",
    }
    OUT_OF_SCOPE_HINTS = {
        "capital of", "weather", "temperature", "movie", "film", "song", "cricket score",
        "stock price", "bitcoin", "programming", "recipe", "restaurant", "travel plan",
    }
    PROFILE_I18N: dict[str, dict[str, str]] = {
        "hi-IN": {
            "To personalize results, please share your location first.": "परिणामों को व्यक्तिगत बनाने के लिए, कृपया पहले अपना स्थान साझा करें।",
            "Which category best matches your need?": "आपकी आवश्यकता के लिए कौन-सी श्रेणी सबसे उपयुक्त है?",
            "Who is the beneficiary for this request?": "इस अनुरोध के लिए लाभार्थी कौन है?",
            "What type of grievance do you want to raise?": "आप किस प्रकार की शिकायत दर्ज करना चाहते हैं?",
            "Delhi": "दिल्ली",
            "Karnataka": "कर्नाटक",
            "Bihar": "बिहार",
            "Maharashtra": "महाराष्ट्र",
            "Tamil Nadu": "तमिलनाडु",
            "Kerala": "केरल",
            "Uttar Pradesh": "उत्तर प्रदेश",
            "Puducherry": "पुडुचेरी",
            "I will type my pincode": "मैं अपना पिनकोड लिखूंगा/लिखूंगी",
            "Farmer schemes": "किसान योजनाएं",
            "Student schemes": "छात्र योजनाएं",
            "Women entrepreneur schemes": "महिला उद्यमी योजनाएं",
            "Citizen services": "नागरिक सेवाएं",
            "Grievance support": "शिकायत सहायता",
            "Myself": "स्वयं",
            "My family": "मेरा परिवार",
            "Community/group": "समुदाय/समूह",
            "Ration/PDS issue": "राशन/पीडीएस समस्या",
            "Certificate/service delay": "प्रमाणपत्र/सेवा में देरी",
            "Benefit/payment delay": "लाभ/भुगतान में देरी",
            "Other grievance": "अन्य शिकायत",
        },
        "es-ES": {
            "To personalize results, please share your location first.": "Para personalizar los resultados, comparte primero tu ubicación.",
            "Which category best matches your need?": "¿Qué categoría se ajusta mejor a tu necesidad?",
            "Who is the beneficiary for this request?": "¿Quién es el beneficiario de esta solicitud?",
            "What type of grievance do you want to raise?": "¿Qué tipo de queja deseas presentar?",
        },
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.kb = KnowledgeBase()
        self.feedback = FeedbackService()
        self.sarvam = SarvamService()
        self.session_language_memory: dict[str, str] = {}
        self.session_history: dict[str, list[dict[str, str]]] = {}
        self.session_last_results: dict[str, list[dict[str, str]]] = {}
        self.session_profiles: dict[str, dict[str, Any]] = {}
        self.session_welcome_sent: set[str] = set()

    def answer(
        self,
        message: str,
        session_id: str,
        channel: str = "web",
        language_code: str | None = None,
        location_hint: str | None = None,
    ) -> dict:
        raw_message = (message or "").strip()
        detection = detect_language(raw_message)
        session_language = self._resolve_session_language(session_id, detection, language_code)
        include_welcome = session_id not in self.session_welcome_sent
        normalized_input = self.sarvam.normalize_user_input(
            text=raw_message,
            detected_language=detection.language_code,
            conversation_id=session_id,
            channel=channel,
        )
        model_message = (normalized_input.get("text") or raw_message).strip()
        history = self.session_history.get(session_id, [])
        if not self._is_in_scope_query(model_message):
            out_text = self._out_of_scope_message()
            translated = self.sarvam.translate_response_text(
                text=out_text,
                source_language="en-IN",
                target_language=session_language,
                conversation_id=session_id,
                channel=channel,
            )
            final_text = translated["text"]
            if include_welcome:
                final_text = self._with_welcome_intro(session_id, final_text)
            self._append_history(session_id, "user", model_message)
            self._append_history(session_id, "assistant", final_text)
            return {
                "session_id": session_id,
                "session_language": session_language,
                "language_code": session_language,
                "detected_language": detection.language_code,
                "detection_confidence": round(float(detection.confidence), 3),
                "location": {
                    "pincode": None,
                    "state": self.settings.default_state,
                    "district": self.settings.default_district,
                    "matched_by": "default",
                },
                "answer": final_text,
                "sources": [],
                "actions": ["out_of_scope"],
                "feedback_token": str(uuid4()),
                "language_trace": {
                    "detected_language": detection.language_code,
                    "input_language": normalized_input.get("source_language", detection.language_code),
                    "input_normalized_to": normalized_input.get("target_language", "en-IN"),
                    "input_translation_applied": normalized_input.get("translated", False),
                    "normalized_user_message": model_message,
                    "sent_response_language": session_language,
                    "received_language": session_language,
                    "mismatch_detected": False,
                    "provider": "scope-guard",
                    "request_payload": {},
                    "translation_payload": translated.get("request_payload", {}),
                    "translated_target_language": translated.get("target_language", session_language),
                },
                "profile": self.session_profiles.get(session_id, self._empty_profile()).copy(),
                "follow_up_question": None,
                "follow_up_options": [],
        }
        profile = self.session_profiles.setdefault(session_id, self._empty_profile())
        self._update_profile_from_message(profile, model_message, location_hint)
        profile["intent"] = self._detect_intent(model_message, history)

        profiling_prompt = self._next_profiling_prompt(profile, model_message, location_hint)
        if profiling_prompt is not None:
            prompt_text, options = profiling_prompt
            final_prompt = self._localize_profile_text(
                text=prompt_text,
                target_language=session_language,
                conversation_id=session_id,
                channel=channel,
            )
            if include_welcome:
                final_prompt = self._with_welcome_intro(session_id, final_prompt)
            localized_options = self._localize_follow_up_options(
                options=options,
                target_language=session_language,
                conversation_id=session_id,
                channel=channel,
            )
            self._append_history(session_id, "user", model_message)
            self._append_history(session_id, "assistant", final_prompt)
            return {
                "session_id": session_id,
                "session_language": session_language,
                "language_code": session_language,
                "detected_language": detection.language_code,
                "detection_confidence": round(float(detection.confidence), 3),
                "location": {
                    "state": profile.get("state") or self.settings.default_state,
                    "district": profile.get("district") or self.settings.default_district,
                    "pincode": profile.get("pincode") or "",
                },
                "answer": final_prompt,
                "sources": [],
                "actions": ["profiling"],
                "feedback_token": str(uuid4()),
                "language_trace": {
                    "detected_language": detection.language_code,
                    "input_language": normalized_input.get("source_language", detection.language_code),
                    "input_normalized_to": normalized_input.get("target_language", "en-IN"),
                    "input_translation_applied": normalized_input.get("translated", False),
                    "normalized_user_message": model_message,
                    "sent_response_language": session_language,
                    "received_language": session_language,
                    "mismatch_detected": False,
                    "provider": "profiling-flow",
                    "request_payload": {},
                    "translation_payload": {},
                    "translated_target_language": session_language,
                },
                "profile": profile.copy(),
                "follow_up_question": final_prompt,
                "follow_up_options": localized_options,
            }

        last_results = self.session_last_results.get(session_id, [])
        contextual_query = self._build_contextual_query(model_message, history, last_results)

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
            query=model_message,
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
        if include_welcome:
            final_answer = self._with_welcome_intro(session_id, final_answer)

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
        self._append_history(session_id, "user", model_message)
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
                "input_language": normalized_input.get("source_language", detection.language_code),
                "input_normalized_to": normalized_input.get("target_language", "en-IN"),
                "input_translation_applied": normalized_input.get("translated", False),
                "normalized_user_message": model_message,
                "sent_response_language": session_language,
                "received_language": received_language,
                "mismatch_detected": mismatch_detected,
                "provider": ai_result.get("provider", "unknown"),
                "request_payload": ai_result.get("request_payload", {}),
                "translation_payload": translated.get("request_payload", {}),
                "translated_target_language": translated.get("target_language", session_language),
            },
            "profile": profile.copy(),
            "follow_up_question": None,
            "follow_up_options": [],
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

    def _empty_profile(self) -> dict[str, Any]:
        return {
            "intent": None,
            "state": None,
            "district": None,
            "pincode": None,
            "location_collected": False,
            "category": None,
            "beneficiary": None,
            "grievance_type": None,
        }

    def _detect_intent(self, message: str, history: list[dict[str, str]]) -> str:
        text = f"{' '.join(h.get('content', '') for h in history[-4:])} {message}".lower()
        if any(token in text for token in ["grievance", "complaint", "issue", "ration", "shikayat"]):
            return "grievance_routing"
        if any(token in text for token in ["eligibility", "eligible", "can i apply", "paatrata"]):
            return "eligibility_check"
        return "scheme_discovery"

    def _update_profile_from_message(self, profile: dict[str, Any], message: str, location_hint: str | None) -> None:
        text = (message or "").lower().strip()
        hint = (location_hint or "").lower()

        resolved = resolve_location(
            text=text,
            location_hint=hint,
            default_state=self.settings.default_state,
            default_district=self.settings.default_district,
        )
        if resolved.get("matched_by") != "default":
            profile["state"] = resolved.get("state")
            profile["district"] = resolved.get("district")
            profile["pincode"] = resolved.get("pincode")
            profile["location_collected"] = True

        if text in {"farmer", "student", "women entrepreneur", "citizen service", "grievance"}:
            profile["category"] = text if text != "grievance" else "grievance"
        if text in {"self", "family", "community"}:
            profile["beneficiary"] = text
        if text in {"ration", "certificate services", "benefit delay", "other grievance"}:
            profile["grievance_type"] = text

        if any(token in text for token in ["farmer", "agriculture", "pm-kisan"]):
            profile["category"] = "farmer"
        elif any(token in text for token in ["student", "education", "scholarship"]):
            profile["category"] = "student"
        elif any(token in text for token in ["women", "woman", "entrepreneur", "udyogini"]):
            profile["category"] = "women entrepreneur"
        elif any(token in text for token in ["citizen service", "certificate", "e-district"]):
            profile["category"] = "citizen service"
        elif "grievance" in text:
            profile["category"] = "grievance"

        if any(token in text for token in ["self", "myself"]):
            profile["beneficiary"] = "self"
        elif any(token in text for token in ["family", "parents", "household"]):
            profile["beneficiary"] = "family"
        elif any(token in text for token in ["community", "group", "village"]):
            profile["beneficiary"] = "community"

        if any(token in text for token in ["ration", "pds"]):
            profile["grievance_type"] = "ration"
        elif any(token in text for token in ["certificate", "document"]):
            profile["grievance_type"] = "certificate services"
        elif any(token in text for token in ["payment", "benefit not received"]):
            profile["grievance_type"] = "benefit delay"

        pincode_match = re.search(r"\b(\d{6})\b", f"{text} {hint}")
        if pincode_match:
            profile["pincode"] = pincode_match.group(1)

    def _next_profiling_prompt(
        self,
        profile: dict[str, Any],
        message: str,
        location_hint: str | None,
    ) -> tuple[str, list[dict[str, str]]] | None:
        has_profile_location = bool(profile.get("location_collected") or profile.get("state") or profile.get("pincode"))
        if not has_profile_location and not self._has_explicit_location(message, location_hint):
            return (
                "To personalize results, please share your location first.",
                [
                    {"value": "Puducherry", "label": "Puducherry"},
                    {"value": "Delhi", "label": "Delhi"},
                    {"value": "Maharashtra", "label": "Maharashtra"},
                    {"value": "Tamil Nadu", "label": "Tamil Nadu"},
                    {"value": "Kerala", "label": "Kerala"},
                    {"value": "I will type my pincode", "label": "I will type my pincode"},
                ],
            )

        if not profile.get("category"):
            return (
                "Which category best matches your need?",
                [
                    {"value": "farmer", "label": "Farmer schemes"},
                    {"value": "student", "label": "Student schemes"},
                    {"value": "women entrepreneur", "label": "Women entrepreneur schemes"},
                    {"value": "citizen service", "label": "Citizen services"},
                    {"value": "grievance", "label": "Grievance support"},
                ],
            )

        if profile.get("intent") in {"scheme_discovery", "eligibility_check"} and not profile.get("beneficiary"):
            return (
                "Who is the beneficiary for this request?",
                [
                    {"value": "self", "label": "Myself"},
                    {"value": "family", "label": "My family"},
                    {"value": "community", "label": "Community/group"},
                ],
            )

        if profile.get("intent") == "grievance_routing" and not profile.get("grievance_type"):
            return (
                "What type of grievance do you want to raise?",
                [
                    {"value": "ration", "label": "Ration/PDS issue"},
                    {"value": "certificate services", "label": "Certificate/service delay"},
                    {"value": "benefit delay", "label": "Benefit/payment delay"},
                    {"value": "other grievance", "label": "Other grievance"},
                ],
            )

        return None

    def _has_explicit_location(self, message: str, location_hint: str | None) -> bool:
        text = f"{(message or '').lower()} {(location_hint or '').lower()}"
        if re.search(r"\b\d{6}\b", text):
            return True
        known_states = [
            "puducherry", "pondicherry", "karaikal", "mahe", "yanam",
            "delhi", "karnataka", "bihar", "maharashtra", "uttar pradesh",
            "tamil nadu", "rajasthan", "west bengal", "gujarat", "kerala",
        ]
        return any(state in text for state in known_states)

    def _localize_follow_up_options(
        self,
        options: list[dict[str, str]],
        target_language: str,
        conversation_id: str,
        channel: str,
    ) -> list[dict[str, str]]:
        localized: list[dict[str, str]] = []
        for opt in options:
            value = opt.get("value", "")
            label = opt.get("label", value)
            translated_text = self._localize_profile_text(
                text=label,
                target_language=target_language,
                conversation_id=conversation_id,
                channel=channel,
            )
            localized.append(
                {
                    "value": value,
                    "label": translated_text,
                }
            )
        return localized

    def _localize_profile_text(
        self,
        text: str,
        target_language: str,
        conversation_id: str,
        channel: str,
    ) -> str:
        normalized = normalize_language_code(target_language) or "en-IN"
        if normalized == "en-IN":
            return text
        mapped = self.PROFILE_I18N.get(normalized, {}).get(text)
        if mapped:
            return mapped
        hardcoded = self._regional_profile_fallback(normalized, text)
        if hardcoded:
            return hardcoded
        translated = self.sarvam.translate_response_text(
            text=text,
            source_language="en-IN",
            target_language=normalized,
            conversation_id=conversation_id,
            channel=channel,
        )
        return translated.get("text", text)

    def _regional_profile_fallback(self, language_code: str, text: str) -> str | None:
        tables: dict[str, dict[str, str]] = {
            "ta-IN": {
                "To personalize results, please share your location first.": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bc7\u0bb5\u0bc8\u0b95\u0bcd\u0b95\u0bc7\u0bb1\u0bcd\u0bb1 \u0bae\u0bc1\u0b9f\u0bbf\u0bb5\u0bc1\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bbe\u0b95, \u0bae\u0bc1\u0ba4\u0bb2\u0bbf\u0bb2\u0bcd \u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b87\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bbf\u0b9f\u0ba4\u0bcd\u0ba4\u0bc8 \u0baa\u0b95\u0bbf\u0bb0\u0bb5\u0bc1\u0bae\u0bcd.",
                "Which category best matches your need?": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bc7\u0bb5\u0bc8\u0b95\u0bcd\u0b95\u0bc1 \u0bae\u0bbf\u0b95\u0bb5\u0bc1\u0bae\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bae\u0bbe\u0ba9 \u0baa\u0bbf\u0bb0\u0bbf\u0bb5\u0bc1 \u0b8e\u0ba4\u0bc1?",
                "Farmer schemes": "\u0bb5\u0bbf\u0bb5\u0bb8\u0bbe\u0baf\u0bbf \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd",
                "Student schemes": "\u0bae\u0bbe\u0ba3\u0bb5\u0bb0\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd",
                "Women entrepreneur schemes": "\u0baa\u0bc6\u0ba3\u0bcd \u0ba4\u0bca\u0bb4\u0bbf\u0bb2\u0bcd\u0bae\u0bc1\u0ba9\u0bc8\u0bb5\u0bcb\u0bb0\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd",
            },
            "te-IN": {
                "To personalize results, please share your location first.": "\u0c35\u0c4d\u0caf\u0c15\u0c4d\u0c24\u0c3f\u0c17\u0c24 \u0c2b\u0c32\u0c3f\u0c24\u0c3e\u0c32 \u0c15\u0c4b\u0c38\u0c02, \u0c2e\u0c41\u0c02\u0c26\u0c41 \u0c2e\u0c40 \u0c38\u0c4d\u0c25\u0c32\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c2a\u0c02\u0c1a\u0c41\u0c15\u0c4b\u0c02\u0c21\u0c3f.",
                "Which category best matches your need?": "\u0c2e\u0c40 \u0c05\u0c35\u0c38\u0c30\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c0f \u0c35\u0c30\u0c4d\u0c17\u0c02 \u0c2c\u0c3e\u0c17\u0c3e \u0c38\u0c30\u0c3f\u0c2a\u0c4b\u0c24\u0c41\u0c02\u0c26\u0c3f?",
                "Farmer schemes": "\u0c30\u0c48\u0c24\u0c41 \u0c2a\u0c25\u0c15\u0c3e\u0c32\u0c41",
                "Student schemes": "\u0c35\u0c3f\u0c26\u0c4d\u0c2f\u0c3e\u0c30\u0c4d\u0c25\u0c3f \u0c2a\u0c25\u0c15\u0c3e\u0c32\u0c41",
                "Women entrepreneur schemes": "\u0c2e\u0c39\u0c3f\u0c33 \u0c09\u0c26\u0c4d\u0c2f\u0c2e\u0c3f\u0c32 \u0c2a\u0c25\u0c15\u0c3e\u0c32\u0c41",
            },
            "kn-IN": {
                "To personalize results, please share your location first.": "\u0cb5\u0cc8\u0caf\u0c95\u0ccd\u0ca4\u0cbf\u0c95\u0cc0\u0c95\u0cc3\u0ca4 \u0cab\u0cb2\u0cbf\u0ca4\u0cbe\u0c82\u0cb6\u0c97\u0cb3\u0cbf\u0c97\u0cc6 \u0cae\u0cca\u0ca6\u0cb2\u0cc1 \u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0cb8\u0ccd\u0ca5\u0cb3\u0cb5\u0ca8\u0ccd\u0ca8\u0cc1 \u0cb9\u0c82\u0c9a\u0cbf\u0c95\u0ccb\u0cb3\u0ccd\u0cb3\u0cbf.",
                "Which category best matches your need?": "\u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0c85\u0cb5\u0cb6\u0ccd\u0caf\u0c95\u0ca4\u0cc6\u0c97\u0cc6 \u0caf\u0cbe\u0cb5 \u0cb5\u0cb0\u0ccd\u0c97 \u0cb9\u0cc6\u0c9a\u0ccd\u0c9a\u0cc1 \u0cb8\u0cc2\u0c95\u0ccd\u0ca4?",
                "Farmer schemes": "\u0cb0\u0cc8\u0ca4 \u0caf\u0ccb\u0c9c\u0ca8\u0cc6\u0c97\u0cb3\u0cc1",
                "Student schemes": "\u0cb5\u0cbf\u0ca6\u0ccd\u0caf\u0cbe\u0cb0\u0ccd\u0ca5\u0cbf \u0caf\u0ccb\u0c9c\u0ca8\u0cc6\u0c97\u0cb3\u0cc1",
                "Women entrepreneur schemes": "\u0cae\u0cb9\u0cbf\u0cb3\u0cbe \u0c89\u0ca6\u0ccd\u0caf\u0cae\u0cbf \u0caf\u0ccb\u0c9c\u0ca8\u0cc6\u0c97\u0cb3\u0cc1",
            },
            "ml-IN": {
                "To personalize results, please share your location first.": "\u0d35\u0d4d\u0d2f\u0d15\u0d4d\u0d24\u0d3f\u0d17\u0d24 \u0d2b\u0d32\u0d19\u0d4d\u0d19\u0d7e\u0d15\u0d4d\u0d15\u0d3e\u0d2f\u0d3f \u0d06\u0d26\u0d4d\u0d2f\u0d02 \u0d28\u0d3f\u0d19\u0d4d\u0d19\u0d33\u0d41\u0d1f\u0d46 \u0d38\u0d4d\u0d25\u0d32\u0d02 \u0d2a\u0d19\u0d4d\u0d15\u0d3f\u0d1f\u0d41\u0d15.",
                "Which category best matches your need?": "\u0d28\u0d3f\u0d19\u0d4d\u0d19\u0d33\u0d41\u0d1f\u0d46 \u0d06\u0d35\u0d36\u0d4d\u0d2f\u0d24\u0d2f\u0d4d\u0d15\u0d4d\u0d15\u0d4d \u0d0f\u0d31\u0d4d\u0d31\u0d35\u0d41\u0d02 \u0d2f\u0d4b\u0d1c\u0d3f\u0d1a\u0d4d\u0d1a \u0d35\u0d3f\u0d2d\u0d3e\u0d17\u0d02 \u0d0f\u0d24\u0d3e\u0d23\u0d4d?",
                "Farmer schemes": "\u0d15\u0d30\u0d4d\u0d37\u0d15 \u0d2a\u0d26\u0d4d\u0d27\u0d24\u0d3f\u0d15\u0d7e",
                "Student schemes": "\u0d35\u0d3f\u0d26\u0d4d\u0d2f\u0d3e\u0d30\u0d4d\u0d25\u0d3f \u0d2a\u0d26\u0d4d\u0d27\u0d24\u0d3f\u0d15\u0d7e",
                "Women entrepreneur schemes": "\u0d35\u0d28\u0d3f\u0d24\u0d3e \u0d09\u0d26\u0d4d\u0d2f\u0d2e\u0d3f \u0d2a\u0d26\u0d4d\u0d27\u0d24\u0d3f\u0d15\u0d7e",
            },
        }
        return tables.get(language_code, {}).get(text)

    def _is_in_scope_query(self, message: str) -> bool:
        text = (message or "").strip().lower()
        if not text:
            return True
        in_scope_hit = any(keyword in text for keyword in self.IN_SCOPE_KEYWORDS)
        out_scope_hit = any(hint in text for hint in self.OUT_OF_SCOPE_HINTS)

        # Keep the guard conservative: only reject when query is clearly out-of-domain
        # and there are no citizen-service signals.
        if out_scope_hit and not in_scope_hit:
            return False

        # Location-like requests are usually in scope for this assistant.
        if re.search(r"\b\d{6}\b", text):
            return True

        # Prefer answering by default to avoid false positives in regional languages.
        return True

    def _out_of_scope_message(self) -> str:
        return (
            "I can help only with Indian government schemes, eligibility, applications, service status, "
            "and grievance routing. Please ask a related citizen-service question."
        )

    def _with_welcome_intro(self, session_id: str, text: str) -> str:
        self.session_welcome_sent.add(session_id)
        intro = (
            "Welcome to JanSahayak, your AI assistant for government schemes and citizen services.\n"
            "JanSahayak mein aapka swagat hai. Main sarkari yojanaon aur nagarik sevaon ke liye aapki sahayata karta hoon."
        )
        if not text.strip():
            return intro
        return f"{intro}\n\n{text}"

    def _language_error(self, language_code: str) -> str:
        if language_code == "hi-IN":
            return "à¤•à¥à¤·à¤®à¤¾ à¤•à¤°à¥‡à¤‚, à¤…à¤­à¥€ à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤­à¤¾à¤·à¤¾ à¤®à¥‡à¤‚ à¤‰à¤¤à¥à¤¤à¤° à¤¬à¤¨à¤¾à¤¨à¥‡ à¤®à¥‡à¤‚ à¤¸à¤®à¤¸à¥à¤¯à¤¾ à¤†à¤ˆà¥¤ à¤•à¥ƒà¤ªà¤¯à¤¾ à¤¦à¥‹à¤¬à¤¾à¤°à¤¾ à¤ªà¥à¤°à¤¯à¤¾à¤¸ à¤•à¤°à¥‡à¤‚à¥¤"
        if language_code == "es-ES":
            return "Lo siento, hubo un problema al generar la respuesta en el idioma solicitado. IntÃ©ntalo de nuevo."
        return "Sorry, there was a problem generating the response in the requested language. Please try again."
