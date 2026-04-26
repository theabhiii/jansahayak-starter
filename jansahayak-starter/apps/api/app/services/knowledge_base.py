from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"
SOURCE_PATH = Path(__file__).resolve().parents[1] / "data" / "gov_sources.json"


class KnowledgeBase:
    STOPWORDS = {
        "the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "and", "or", "with", "by",
        "me", "my", "i", "we", "you", "please", "show", "tell", "need", "want", "about", "what",
        "which", "how", "can", "do", "does", "this", "that", "it", "service", "scheme", "schemes",
    }
    CATEGORY_HINTS = {
        "farmer": {"farmer", "farm", "farming", "agriculture", "agri", "kisan", "crop", "pm", "pmkisan"},
        "student": {"student", "students", "education", "scholarship", "college", "study", "loan", "credit"},
        "women entrepreneur": {"women", "woman", "female", "entrepreneur", "business", "employment", "udyogini"},
        "citizen service": {"citizen", "certificate", "document", "documents", "edistrict", "district", "services"},
        "grievance": {"grievance", "complaint", "issue", "problem", "delay", "ration", "pds", "support"},
    }
    INTENT_HINTS = {
        "scheme_discovery": {"scheme", "benefit", "subsidy", "yojana"},
        "eligibility_check": {"eligibility", "eligible", "criteria", "apply", "application", "documents"},
        "grievance_routing": {"grievance", "complaint", "portal", "department", "issue"},
    }

    def __init__(self) -> None:
        self.records = self._load()
        self.gov_sources = self._load_sources()

    def _load(self) -> List[Dict[str, Any]]:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_sources(self) -> List[Dict[str, Any]]:
        if not SOURCE_PATH.exists():
            return []
        with open(SOURCE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def search(
        self,
        query: str,
        state: str,
        district: str,
        profile: Dict[str, Any] | None = None,
        intent: str | None = None,
    ) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        query_tokens = self._expanded_query_tokens(q, profile=profile, intent=intent)
        category_hint = self._resolve_query_category(q, profile)
        normalized_query = self._normalized_text(q)
        local_scored = []
        global_scored = []
        for record in self.records:
            title = (record.get("title") or "").lower()
            category = (record.get("category") or "").lower()
            eligibility = (record.get("eligibility") or "").lower()
            benefits = (record.get("benefits") or "").lower()
            application = (record.get("application") or "").lower()
            grievance_office = (record.get("grievance_office") or "").lower()

            # Weighted relevance so title/category intent beats generic national schemes.
            score = 0
            score += self._token_overlap_score(query_tokens, self._tokens(title), weight=6)
            score += self._token_overlap_score(query_tokens, self._tokens(category), weight=5)
            score += self._token_overlap_score(query_tokens, self._tokens(eligibility), weight=2)
            score += self._token_overlap_score(query_tokens, self._tokens(benefits), weight=2)
            score += self._token_overlap_score(query_tokens, self._tokens(application), weight=2)
            score += self._token_overlap_score(query_tokens, self._tokens(grievance_office), weight=2)
            score += self._phrase_match_score(normalized_query, self._normalized_text(title), weight=10)

            if category_hint and category == category_hint:
                score += 9
            if intent == "grievance_routing" and category == "grievance":
                score += 8
            if intent == "eligibility_check" and ("eligibility" in eligibility or "eligible" in eligibility):
                score += 4
            if intent == "eligibility_check" and ("application" in application or "apply" in application):
                score += 2

            state_match = record["states"] == ["All"] or state in record["states"]
            district_match = record["districts"] == ["All"] or district in record["districts"]

            if state in record["states"]:
                score += 6
            elif state_match:
                score += 2
            if district_match:
                score += 2

            if score <= 0:
                continue

            if state_match and district_match:
                local_scored.append((score + 2, record))
            elif state_match:
                local_scored.append((score, record))
            else:
                # Keep out-of-state items as low-priority fallback only.
                global_scored.append((max(1, score - 2), record))

        local_scored.sort(key=lambda item: item[0], reverse=True)
        global_scored.sort(key=lambda item: item[0], reverse=True)

        if category_hint:
            local_category_matches = [
                item[1]
                for item in local_scored
                if (item[1].get("category") or "").lower() == category_hint
            ][:3]
            if local_category_matches:
                return local_category_matches

            global_category_matches = [
                item[1]
                for item in global_scored
                if (item[1].get("category") or "").lower() == category_hint
            ][:3]
            if global_category_matches:
                return global_category_matches

        local_results = [item[1] for item in local_scored[:3]]
        if len(local_results) >= 2:
            return local_results

        needed = 3 - len(local_results)
        fallback = [item[1] for item in global_scored[:needed]]
        return local_results + fallback

    def discover_sources(
        self,
        query: str,
        state: str,
        limit: int = 8,
        profile: Dict[str, Any] | None = None,
        intent: str | None = None,
    ) -> List[Dict[str, str]]:
        q = (query or "").lower()
        query_tokens = self._expanded_query_tokens(q, profile=profile, intent=intent)
        ranked: List[tuple[int, Dict[str, Any]]] = []
        for src in self.gov_sources:
            hay = " ".join(
                [
                    src.get("title", ""),
                    " ".join(src.get("categories", [])),
                    src.get("level", ""),
                ]
            ).lower()
            score = self._token_overlap_score(query_tokens, self._tokens(hay), weight=2)
            if src.get("states") == ["All"]:
                score += 2
            elif state in src.get("states", []):
                score += 4
            if score > 0:
                ranked.append((score, src))

        ranked.sort(key=lambda pair: pair[0], reverse=True)
        top = [pair[1] for pair in ranked[:limit]]
        return [
            {
                "id": src.get("id", ""),
                "title": src.get("title", src.get("url", "")),
                "url": src.get("url", ""),
            }
            for src in top
            if src.get("url")
        ]

    def _tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(token) > 1 and token not in self.STOPWORDS
        }

    def _token_overlap_score(self, query_tokens: set[str], text_tokens: set[str], weight: int = 1) -> int:
        if not query_tokens or not text_tokens:
            return 0
        return len(query_tokens & text_tokens) * weight

    def _expanded_query_tokens(
        self,
        query: str,
        profile: Dict[str, Any] | None = None,
        intent: str | None = None,
    ) -> set[str]:
        tokens = set(self._tokens(query))
        category = self._resolve_query_category(query, profile)
        if category:
            tokens.update(self.CATEGORY_HINTS.get(category, set()))

        resolved_intent = (intent or "").strip().lower()
        if resolved_intent:
            tokens.update(self.INTENT_HINTS.get(resolved_intent, set()))

        beneficiary = ((profile or {}).get("beneficiary") or "").strip().lower()
        if beneficiary == "family":
            tokens.update({"family", "household"})
        elif beneficiary == "community":
            tokens.update({"community", "group", "village"})

        grievance_type = ((profile or {}).get("grievance_type") or "").strip().lower()
        if grievance_type == "certificate services":
            tokens.update({"certificate", "document", "documents", "service", "services"})
        elif grievance_type == "benefit delay":
            tokens.update({"benefit", "payment", "delay"})
        elif grievance_type:
            tokens.update(self._tokens(grievance_type))

        return tokens

    def _resolve_query_category(self, query: str, profile: Dict[str, Any] | None = None) -> str | None:
        profile_category = ((profile or {}).get("category") or "").strip().lower()
        if profile_category in self.CATEGORY_HINTS:
            return profile_category

        query_tokens = self._tokens(query)
        best_match: str | None = None
        best_score = 0
        for category, hints in self.CATEGORY_HINTS.items():
            score = len(query_tokens & hints)
            if score > best_score:
                best_match = category
                best_score = score
        return best_match

    def _normalized_text(self, text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))

    def _phrase_match_score(self, query_text: str, record_text: str, weight: int = 1) -> int:
        if not query_text or not record_text:
            return 0

        compact_query = " ".join(self._tokens(query_text))
        if compact_query and compact_query in record_text:
            return weight

        overlap_phrases = {
            "pm kisan",
            "student credit card",
            "e district",
            "aaple sarkar",
            "grievance support",
        }
        if any(phrase in query_text and phrase in record_text for phrase in overlap_phrases):
            return weight
        return 0
