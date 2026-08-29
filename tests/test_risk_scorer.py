from unittest.mock import MagicMock
import numpy as np
import pytest
from src.models import ComplaintAnalysis, Patient, VitalSigns
from src.risk_scorer import HybridRiskScorer


def test_escalation_under_uncertainty():
    scorer = HybridRiskScorer()
    # Mock model that predicts ESI 3 with 0.6 confidence (below 0.70 threshold)
    mock_model = MagicMock()
    mock_model.classes_ = np.array([1, 2, 3, 4, 5])
    mock_model.predict_proba.return_value = np.array([[0.05, 0.15, 0.60, 0.10, 0.10]])
    scorer.model = mock_model

    patient = Patient(name="John Doe", age=45, sex="M", chief_complaint="abdominal pain")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=75,
        respiratory_rate=16,
        spo2=98.0,
        systolic_bp=120,
        diastolic_bp=80,
        temperature=37.0,
        pain_score=3,
        consciousness="A",
    )
    analysis = ComplaintAnalysis(
        red_flags=[],
        justification="Mild abdominal pain",
        suggested_esi=3,
        confidence=0.5,
    )
    result = scorer.score(patient, vitals, analysis, resources_needed=2)
    # Should escalate from ESI 3 to ESI 2 due to ml_confidence < 0.70
    assert result.esi_level == 2


def test_red_flag_forces_esi_2():
    scorer = HybridRiskScorer()
    patient = Patient(
        name="Jane Smith",
        age=52,
        sex="F",
        chief_complaint="epigastric discomfort and nausea",
    )
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=75,
        respiratory_rate=16,
        spo2=98.0,
        systolic_bp=120,
        diastolic_bp=80,
        temperature=37.0,
        pain_score=3,
        consciousness="A",
    )
    analysis = ComplaintAnalysis(
        red_flags=["ATYPICAL_CARDIAC_FEMALE"],
        justification="Atypical cardiac presentation in female 40+",
        suggested_esi=2,
        confidence=0.8,
    )
    result = scorer.score(patient, vitals, analysis, resources_needed=2)
    assert result.esi_level == 2
    assert "ATYPICAL_CARDIAC_FEMALE" in result.red_flags


def test_esi_1_not_overridden():
    scorer = HybridRiskScorer()
    mock_model = MagicMock()
    mock_model.classes_ = np.array([1, 2, 3, 4, 5])
    # ML wrongly thinks ESI 4 with high confidence
    mock_model.predict_proba.return_value = np.array([[0.0, 0.0, 0.1, 0.85, 0.05]])
    scorer.model = mock_model

    patient = Patient(name="Unresponsive Person", age=60, sex="M", chief_complaint="unconscious")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=45,
        respiratory_rate=6,
        spo2=72.0,
        systolic_bp=50,
        diastolic_bp=30,
        temperature=35.0,
        consciousness="U",
    )
    analysis = ComplaintAnalysis(
        red_flags=["Unresponsive"],
        justification="Critical unresponsive patient",
        suggested_esi=1,
        confidence=0.9,
    )
    result = scorer.score(patient, vitals, analysis, resources_needed=2)
    assert result.esi_level == 1


def test_confidence_range():
    scorer = HybridRiskScorer()
    patient = Patient(name="Test Patient", age=30, sex="M")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=70,
        respiratory_rate=14,
        spo2=99.0,
        systolic_bp=115,
        diastolic_bp=75,
        temperature=36.8,
    )
    analysis = ComplaintAnalysis()
    result = scorer.score(patient, vitals, analysis, resources_needed=0)
    assert 0.0 <= result.confidence <= 1.0


def test_justification_not_empty():
    scorer = HybridRiskScorer()
    patient = Patient(name="Test Patient", age=30, sex="M")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=70,
        respiratory_rate=14,
        spo2=99.0,
        systolic_bp=115,
        diastolic_bp=75,
        temperature=36.8,
    )
    analysis = ComplaintAnalysis()
    result = scorer.score(patient, vitals, analysis, resources_needed=1)
    assert len(result.justification.strip()) > 0


def test_justification_max_10_words():
    scorer = HybridRiskScorer()
    patient = Patient(name="Test Patient", age=30, sex="M", chief_complaint="very long chief complaint with multiple distinct issues")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=70,
        respiratory_rate=14,
        spo2=99.0,
        systolic_bp=115,
        diastolic_bp=75,
        temperature=36.8,
    )
    analysis = ComplaintAnalysis(
        justification="This is an extremely detailed sentence that goes well beyond the standard limit of ten words for justification",
        confidence=0.85,
    )
    result = scorer.score(patient, vitals, analysis, resources_needed=2)
    word_count = len(result.justification.split())
    assert word_count <= 10
