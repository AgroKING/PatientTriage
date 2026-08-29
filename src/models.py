from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import uuid
from pydantic import BaseModel, Field


class Patient(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    age: float
    sex: Literal["M", "F"]
    arrival_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chief_complaint: str = ""
    medical_history: str = ""
    status: Literal["WAITING", "IN_TREATMENT", "FAST_TRACK", "DISCHARGED"] = "WAITING"
    current_esi: int | None = None


class VitalSigns(BaseModel):
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: int
    respiratory_rate: int
    spo2: float
    systolic_bp: int
    diastolic_bp: int
    temperature: float
    pain_score: int = 0
    consciousness: Literal["A", "V", "P", "U"] = "A"
    supplemental_o2: bool = False


class ComplaintAnalysis(BaseModel):
    red_flags: list[str] = Field(default_factory=list)
    symptom_onset_hours: float | None = None
    justification: str = ""
    suggested_esi: int | None = None
    confidence: float = 0.0


class TriageResult(BaseModel):
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    esi_level: int
    news2_score: int
    confidence: float
    justification: str
    red_flags: list[str] = Field(default_factory=list)
    is_override: bool = False
    override_reason: str | None = None
    override_note: str | None = None


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    patient_id: str
    clinician_id: str
    event_type: Literal["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"]
    ai_esi: int
    ai_confidence: float
    ai_justification: str
    final_esi: int
    override_reason_code: str | None = None
    override_note: str | None = None
    dwell_seconds: float | None = None
    vitals_snapshot: dict = Field(default_factory=dict)
