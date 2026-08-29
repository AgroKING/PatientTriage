import json
import os
import re
import config
from src.models import ComplaintAnalysis


class LLMEngine:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = None
        self.use_fallback = False

        if not self.api_key:
            self.use_fallback = True
        else:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key, timeout=config.GROQ_TIMEOUT)
                self.use_fallback = False
            except Exception:
                self.use_fallback = True

    def analyze_complaint(self, text: str, age: float, sex: str) -> ComplaintAnalysis:
        if self.use_fallback or not self.client:
            return self._keyword_fallback(text, age, sex)
        try:
            return self._groq_analyze(text, age, sex)
        except Exception:
            return self._keyword_fallback(text, age, sex)

    def _groq_analyze(self, text: str, age: float, sex: str) -> ComplaintAnalysis:
        system_prompt = f"""You are an emergency department triage assistant. Analyze the chief complaint
and return ONLY a JSON object with these fields:
- red_flags: list of clinical red flag strings (e.g., "Atypical cardiac presentation")
- symptom_onset_hours: number or null
- justification: string, MAX 10 words, clinical shorthand (e.g., "Sepsis risk: temp 101 + HR 115 + age 72")
- suggested_esi: integer 1-5 or null
- confidence: float 0.0-1.0

Patient: {age} year old {sex}.
Chief complaint: {text}

Return ONLY valid JSON, no markdown."""

        completion = self.client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze complaint: {text}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=config.GROQ_MAX_TOKENS,
            timeout=config.GROQ_TIMEOUT,
        )
        content = completion.choices[0].message.content
        data = json.loads(content)

        justification = data.get("justification", "")
        if justification:
            words = str(justification).split()
            justification = " ".join(words[:10])

        return ComplaintAnalysis(
            red_flags=data.get("red_flags", []),
            symptom_onset_hours=data.get("symptom_onset_hours"),
            justification=justification,
            suggested_esi=data.get("suggested_esi"),
            confidence=float(data.get("confidence", 0.8)),
        )

    def _keyword_fallback(self, text: str, age: float, sex: str) -> ComplaintAnalysis:
        text_lower = text.lower()
        red_flags: list[str] = []
        suggested_esi: int | None = None
        matched_tags: list[str] = []

        trauma_match = any(k in text_lower for k in config.TRAUMA_KEYWORDS)
        stroke_match = any(k in text_lower for k in config.STROKE_KEYWORDS)
        cardiac_match = any(k in text_lower for k in config.CARDIAC_FEMALE_KEYWORDS)
        sepsis_match = any(k in text_lower for k in config.SEPSIS_KEYWORDS)
        resp_match = any(k in text_lower for k in config.RESPIRATORY_KEYWORDS)

        if trauma_match:
            red_flags.append("Trauma mechanism: high energy injury")
            matched_tags.append("Trauma")
            suggested_esi = 1
        elif stroke_match:
            red_flags.append("Acute neurological deficit / stroke alert")
            matched_tags.append("Stroke alert")
            suggested_esi = 2
        elif cardiac_match and sex == "F" and age >= 40:
            red_flags.append("Atypical cardiac presentation in female 40+")
            matched_tags.append("Atypical cardiac")
            suggested_esi = 2
        elif sepsis_match and age >= 65:
            red_flags.append("Geriatric sepsis / altered mental status")
            matched_tags.append("Sepsis risk")
            suggested_esi = 2
        elif resp_match:
            red_flags.append("Acute respiratory compromise")
            matched_tags.append("Respiratory distress")
            suggested_esi = 2
        elif cardiac_match or sepsis_match:
            matched_tags.append("Acuity 3 symptom")
            suggested_esi = 3

        if matched_tags:
            justification = f"Keyword match: {', '.join(matched_tags)}"
        else:
            justification = "Standard presentation without red flag keywords"

        words = justification.split()
        justification = " ".join(words[:10])

        return ComplaintAnalysis(
            red_flags=red_flags,
            symptom_onset_hours=None,
            justification=justification,
            suggested_esi=suggested_esi,
            confidence=0.5,
        )
