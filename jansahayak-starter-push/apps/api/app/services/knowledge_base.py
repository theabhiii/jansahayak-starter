from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"


class KnowledgeBase:
    def __init__(self) -> None:
        self.records = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def search(self, query: str, state: str, district: str) -> List[Dict[str, Any]]:
        q = query.lower()
        scored = []
        for record in self.records:
            text = " ".join([
                record["title"],
                record["category"],
                record["eligibility"],
                record["benefits"],
                record["application"],
                record["grievance_office"],
            ]).lower()
            score = sum(1 for token in q.split() if token in text)
            if record["states"] == ["All"] or state in record["states"]:
                score += 2
            if record["districts"] == ["All"] or district in record["districts"]:
                score += 1
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:3]]
