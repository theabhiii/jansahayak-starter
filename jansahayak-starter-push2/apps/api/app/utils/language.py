from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

SUPPORTED_LANGUAGES = {
    "as-IN": "Assamese",
    "bn-IN": "Bengali",
    "brx-IN": "Bodo",
    "doi-IN": "Dogri",
    "en-IN": "English",
    "es-ES": "Spanish",
    "gu-IN": "Gujarati",
    "hi-IN": "Hindi",
    "kn-IN": "Kannada",
    "ks-IN": "Kashmiri",
    "kok-IN": "Konkani",
    "mai-IN": "Maithili",
    "ml-IN": "Malayalam",
    "mni-IN": "Manipuri",
    "mr-IN": "Marathi",
    "ne-IN": "Nepali",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "sa-IN": "Sanskrit",
    "sat-IN": "Santali",
    "sd-IN": "Sindhi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ur-IN": "Urdu",
}

SCRIPT_RANGES = {
    "hi-IN": [("\u0900", "\u097F"), ("\uA8E0", "\uA8FF"), ("\U00011B00", "\U00011B5F")],
    "bn-IN": [("\u0980", "\u09FF")],
    "pa-IN": [("\u0A00", "\u0A7F")],
    "gu-IN": [("\u0A80", "\u0AFF")],
    "od-IN": [("\u0B00", "\u0B7F")],
    "ta-IN": [("\u0B80", "\u0BFF")],
    "te-IN": [("\u0C00", "\u0C7F")],
    "kn-IN": [("\u0C80", "\u0CFF")],
    "ml-IN": [("\u0D00", "\u0D7F")],
    "ur-IN": [("\u0600", "\u06FF"), ("\u0750", "\u077F"), ("\u08A0", "\u08FF"), ("\uFB50", "\uFDFF"), ("\uFE70", "\uFEFF")],
    "sd-IN": [("\u0600", "\u06FF"), ("\u0750", "\u077F"), ("\u08A0", "\u08FF"), ("\uFB50", "\uFDFF"), ("\uFE70", "\uFEFF")],
}

LANGUAGE_HINTS = {
    "hi-IN": ["yojana", "sarkar", "patrata", "yojna", "shikayat"],
    "mr-IN": ["majha", "yojana", "maharashtra", "arj", "labh"],
    "bn-IN": ["ami", "sarkari", "prokolpo", "joggo", "abedon"],
    "ta-IN": ["thittam", "udhavi", "vinnappam", "thamizh"],
    "te-IN": ["pathakam", "sahayam", "darakastu", "telugu"],
    "kn-IN": ["yojane", "arji", "sahaya", "kannada"],
    "ml-IN": ["padhathi", "sahaya", "apeksha", "malayalam"],
    "gu-IN": ["yojana", "arji", "madad", "gujarat"],
    "pa-IN": ["yojana", "arzi", "madad", "punjab"],
    "od-IN": ["yojana", "abedana", "sahayata", "odisha"],
    "ur-IN": ["madad", "sarkari", "darkhast", "shikayat"],
    "en-IN": ["scheme", "eligibility", "application", "grievance", "status", "benefits", "help", "citizen"],
    "es-ES": ["esquema", "subsidio", "elegibilidad", "solicitud", "queja", "beneficios", "ayuda", "gobierno"],
}

ENGLISH_MARKERS = {"the", "and", "for", "please", "need", "from", "scheme", "application", "status", "help", "citizen", "grievance"}
SPANISH_MARKERS = {"el", "la", "de", "para", "por", "ayuda", "gobierno", "solicitud", "elegibilidad", "estado", "beneficios", "queja"}


@dataclass
class LanguageDetectionResult:
    language_code: str
    confidence: float


def _in_range(ch: str, start: str, end: str) -> bool:
    return ord(start) <= ord(ch) <= ord(end)


def normalize_language_code(language_code: str | None) -> str | None:
    if not language_code:
        return None
    cleaned = language_code.strip().replace("_", "-")
    if not cleaned:
        return None
    # Normalize common Odia alias used by older specs.
    if cleaned.lower() == "or-in":
        cleaned = "od-IN"

    parts = cleaned.split("-")
    if len(parts) == 1:
        primary = parts[0].lower()
        for code in SUPPORTED_LANGUAGES:
            if code.startswith(f"{primary}-"):
                return code
        return None

    primary = parts[0].lower()
    region = parts[1].upper()
    normalized = f"{primary}-{region}"
    if normalized == "or-IN":
        normalized = "od-IN"
    return normalized if normalized in SUPPORTED_LANGUAGES else None


def detect_language(text: str) -> LanguageDetectionResult:
    if not text or not text.strip():
        return LanguageDetectionResult(language_code="en-IN", confidence=0.0)

    script_counter: Counter[str] = Counter()
    for ch in text:
        for lang, ranges in SCRIPT_RANGES.items():
            if any(_in_range(ch, start, end) for start, end in ranges):
                script_counter[lang] += 1

    if script_counter:
        top_lang, count = script_counter.most_common(1)[0]
        if count >= 2:
            if top_lang in ("hi-IN", "ur-IN", "sd-IN"):
                text_l = text.lower()
                if top_lang == "hi-IN" and re.search(r"[\u0600-\u06FF]", text):
                    return LanguageDetectionResult(language_code="ur-IN", confidence=0.92)
                if top_lang in ("ur-IN", "sd-IN") and re.search(r"[\u0900-\u097F]", text):
                    return LanguageDetectionResult(language_code="hi-IN", confidence=0.92)
                if "sindh" in text_l:
                    return LanguageDetectionResult(language_code="sd-IN", confidence=0.86)
            return LanguageDetectionResult(language_code=top_lang, confidence=min(0.98, 0.74 + (count / 80)))

    text_l = text.lower()
    words = re.findall(r"[a-zA-Z\u00C0-\u017F]+", text_l)

    if words:
        en_score = sum(1 for w in words if w in ENGLISH_MARKERS)
        es_score = sum(1 for w in words if w in SPANISH_MARKERS)
        has_spanish_chars = bool(re.search(r"[\u00E1\u00E9\u00ED\u00F3\u00FA\u00F1\u00FC]", text_l))
        if es_score > en_score and (es_score >= 1 or has_spanish_chars):
            confidence = min(0.9, 0.5 + (es_score * 0.1) + (0.08 if has_spanish_chars else 0))
            return LanguageDetectionResult(language_code="es-ES", confidence=confidence)
        if en_score > es_score and en_score >= 1:
            confidence = min(0.88, 0.5 + (en_score * 0.09))
            return LanguageDetectionResult(language_code="en-IN", confidence=confidence)

    hint_scores: Counter[str] = Counter()
    for lang, hints in LANGUAGE_HINTS.items():
        for token in hints:
            if token in text_l:
                hint_scores[lang] += 1

    if hint_scores:
        top_lang, score = hint_scores.most_common(1)[0]
        if score > 0:
            confidence = min(0.85, 0.42 + (score * 0.14))
            return LanguageDetectionResult(language_code=top_lang, confidence=confidence)

    if words and not re.search(r"[\u00E1\u00E9\u00ED\u00F3\u00FA\u00F1\u00FC]", text_l):
        return LanguageDetectionResult(language_code="en-IN", confidence=0.46)

    return LanguageDetectionResult(language_code="en-IN", confidence=0.26)


def choose_output_language(user_requested: str | None, detected: str) -> str:
    requested = normalize_language_code(user_requested)
    if requested:
        return requested
    detected_normalized = normalize_language_code(detected)
    return detected_normalized or "en-IN"
