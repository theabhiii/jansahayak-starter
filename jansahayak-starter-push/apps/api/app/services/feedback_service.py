from __future__ import annotations

from typing import Dict, List


class FeedbackService:
    def improve_answer(
        self,
        question: str,
        original_answer: str,
        reason: str | None,
        sources: List[Dict],
        location: dict,
        language_code: str,
    ) -> str:
        source_titles = ", ".join(source["title"] for source in sources) if sources else "relevant government scheme records"

        if language_code == "hi-IN":
            reason_line = f" सुधार का कारण: {reason}." if reason else ""
            return (
                f"सरल भाषा में: {original_answer} "
                f"यह उत्तर {location['district']}, {location['state']} के आधार पर बेहतर किया गया है। "
                f"मैंने इन स्रोतों को फिर से जाँचा: {source_titles}.{reason_line} "
                "अगर चाहें तो मैं आगे पात्रता चरण, जरूरी दस्तावेज़, या शिकायत रूटिंग बता सकता हूँ।"
            )

        if language_code == "es-ES":
            reason_line = f" Motivo de mejora: {reason}." if reason else ""
            return (
                f"En términos simples: {original_answer} "
                f"Esta respuesta fue refinada para {location['district']}, {location['state']}. "
                f"También revisé estas fuentes: {source_titles}.{reason_line} "
                "Si quieres, puedo compartir los pasos de elegibilidad, documentos y ruta de queja."
            )

        reason_line = f" Reason for retry: {reason}." if reason else ""
        return (
            f"In simple terms: {original_answer} "
            f"This answer is refined for {location['district']}, {location['state']}. "
            f"I also re-checked these sources: {source_titles}.{reason_line} "
            "If you want, I can next give eligibility steps, required documents, or grievance routing."
        )
