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

    def search(self, query: str, state: str, district: str) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        query_tokens = self._tokens(q)
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

        local_results = [item[1] for item in local_scored[:3]]
        if len(local_results) >= 2:
            return local_results

        needed = 3 - len(local_results)
        fallback = [item[1] for item in global_scored[:needed]]
        return local_results + fallback

    def discover_sources(self, query: str, state: str, limit: int = 8) -> List[Dict[str, str]]:
        q = (query or "").lower()
        query_tokens = self._tokens(q)
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
