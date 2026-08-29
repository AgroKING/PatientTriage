from datetime import datetime, timedelta, timezone
import pytest
from src.database import (
    get_audit_trail,
    init_db,
    insert_audit_log,
    insert_patient,
    insert_vitals,
)
from src.llm_engine import LLMEngine
from src.models import AuditEntry, ComplaintAnalysis, Patient, VitalSigns
from src.queue_manager import get_ranked_queue
from src.risk_scorer import HybridRiskScorer
from src.surge_manager import SurgeManager


@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "triage_test.db")
    conn = init_db(db_path)
    return conn


def generate_sample_patients(conn):
    cases = [
        # ESI 1 - Unresponsive / Shock
        (
            Patient(name="Alice Shock", age=50, sex="F", chief_complaint="Unresponsive and cold to touch", current_esi=1),
            VitalSigns(patient_id="", heart_rate=35, respiratory_rate=8, spo2=75, systolic_bp=55, diastolic_bp=30, temperature=34.5, consciousness="U"),
        ),
        (
            Patient(name="Bob Trauma", age=28, sex="M", chief_complaint="MVA crush injury severe respiratory distress", current_esi=1),
            VitalSigns(patient_id="", heart_rate=145, respiratory_rate=38, spo2=82, systolic_bp=80, diastolic_bp=50, temperature=36.2, consciousness="P"),
        ),
        # ESI 2 - Atypical cardiac female 40+
        (
            Patient(name="Carol Cardiac", age=54, sex="F", chief_complaint="Jaw pain, epigastric discomfort, persistent nausea", current_esi=2),
            VitalSigns(patient_id="", heart_rate=88, respiratory_rate=18, spo2=97, systolic_bp=135, diastolic_bp=85, temperature=36.8, pain_score=6),
        ),
        # ESI 2 - Geriatric sepsis
        (
            Patient(name="David Sepsis", age=78, sex="M", chief_complaint="Confused, lethargic, not acting right", current_esi=2),
            VitalSigns(patient_id="", heart_rate=112, respiratory_rate=24, spo2=93, systolic_bp=95, diastolic_bp=55, temperature=35.4, consciousness="V"),
        ),
        # ESI 2 - Pediatric tachycardia
        (
            Patient(name="Eva Peds", age=4, sex="F", chief_complaint="High fever and rapid breathing", current_esi=2),
            VitalSigns(patient_id="", heart_rate=165, respiratory_rate=36, spo2=94, systolic_bp=85, diastolic_bp=55, temperature=39.2, pain_score=7),
        ),
        # ESI 2 - Severe pain
        (
            Patient(name="Frank Pain", age=35, sex="M", chief_complaint="Acute renal colic severe flank pain", current_esi=2),
            VitalSigns(patient_id="", heart_rate=95, respiratory_rate=18, spo2=98, systolic_bp=140, diastolic_bp=90, temperature=37.0, pain_score=9),
        ),
        # ESI 2 - Silent MI diabetic
        (
            Patient(name="Grace Diabetic", age=62, sex="F", chief_complaint="Profuse sweating, sudden dyspnea, extreme weakness", medical_history="Type 2 diabetes", current_esi=2),
            VitalSigns(patient_id="", heart_rate=105, respiratory_rate=22, spo2=93, systolic_bp=130, diastolic_bp=82, temperature=36.9, pain_score=2),
        ),
        # ESI 3 - Moderate abdominal pain (multi-resource)
        (
            Patient(name="Henry Abdo", age=42, sex="M", chief_complaint="Right lower quadrant abdominal pain for 6 hours", current_esi=3),
            VitalSigns(patient_id="", heart_rate=80, respiratory_rate=16, spo2=99, systolic_bp=125, diastolic_bp=80, temperature=37.2, pain_score=4),
        ),
        (
            Patient(name="Iris Headache", age=31, sex="F", chief_complaint="Moderate migraine with light sensitivity", current_esi=3),
            VitalSigns(patient_id="", heart_rate=76, respiratory_rate=15, spo2=98, systolic_bp=118, diastolic_bp=75, temperature=36.8, pain_score=5),
        ),
        (
            Patient(name="Jack Fracture", age=22, sex="M", chief_complaint="Closed wrist deformity after skateboard fall", current_esi=3),
            VitalSigns(patient_id="", heart_rate=84, respiratory_rate=16, spo2=99, systolic_bp=128, diastolic_bp=82, temperature=36.7, pain_score=6),
        ),
        (
            Patient(name="Karen Asthma", age=29, sex="F", chief_complaint="Mild asthma flare responsive to inhaler", medical_history="Asthma", current_esi=3),
            VitalSigns(patient_id="", heart_rate=88, respiratory_rate=20, spo2=96, systolic_bp=120, diastolic_bp=80, temperature=37.0, pain_score=2),
        ),
        (
            Patient(name="Leo Vomit", age=50, sex="M", chief_complaint="Nausea and vomiting x 2 days", current_esi=3),
            VitalSigns(patient_id="", heart_rate=85, respiratory_rate=16, spo2=98, systolic_bp=115, diastolic_bp=75, temperature=37.3, pain_score=3),
        ),
        (
            Patient(name="Mona Cellulitis", age=60, sex="F", chief_complaint="Redness and swelling in right lower leg", current_esi=3),
            VitalSigns(patient_id="", heart_rate=82, respiratory_rate=16, spo2=98, systolic_bp=130, diastolic_bp=80, temperature=37.6, pain_score=4),
        ),
        (
            Patient(name="Ned ZeroHist", age=38, sex="M", chief_complaint="Persistent abdominal cramps and nausea", medical_history="", current_esi=3),
            VitalSigns(patient_id="", heart_rate=78, respiratory_rate=16, spo2=98, systolic_bp=120, diastolic_bp=80, temperature=37.0, pain_score=3),
        ),
        (
            Patient(name="Olivia UTI", age=26, sex="F", chief_complaint="Dysuria and urinary frequency", current_esi=3),
            VitalSigns(patient_id="", heart_rate=74, respiratory_rate=14, spo2=99, systolic_bp=110, diastolic_bp=70, temperature=37.1, pain_score=3),
        ),
        # ESI 4 - Simple resources (e.g. simple laceration / xray)
        (
            Patient(name="Paul Cut", age=19, sex="M", chief_complaint="Clean finger laceration from kitchen knife", current_esi=4),
            VitalSigns(patient_id="", heart_rate=72, respiratory_rate=14, spo2=99, systolic_bp=118, diastolic_bp=76, temperature=36.7, pain_score=2),
        ),
        (
            Patient(name="Quinn Ankle", age=25, sex="F", chief_complaint="Twisted ankle while jogging", current_esi=4),
            VitalSigns(patient_id="", heart_rate=70, respiratory_rate=14, spo2=99, systolic_bp=116, diastolic_bp=74, temperature=36.6, pain_score=3),
        ),
        (
            Patient(name="Rita Ear", age=6, sex="F", chief_complaint="Left ear pain and discharge", current_esi=4),
            VitalSigns(patient_id="", heart_rate=90, respiratory_rate=20, spo2=99, systolic_bp=98, diastolic_bp=62, temperature=37.5, pain_score=3),
        ),
        (
            Patient(name="Sam Rash", age=45, sex="M", chief_complaint="Localized poison ivy rash on forearm", current_esi=4),
            VitalSigns(patient_id="", heart_rate=68, respiratory_rate=14, spo2=99, systolic_bp=122, diastolic_bp=78, temperature=36.8, pain_score=1),
        ),
        # ESI 5 - Fast track / Refills / Exam only
        (
            Patient(name="Tina Suture", age=33, sex="F", chief_complaint="Suture removal from healed wound", current_esi=5),
            VitalSigns(patient_id="", heart_rate=65, respiratory_rate=12, spo2=99, systolic_bp=114, diastolic_bp=72, temperature=36.6, pain_score=0),
        ),
        (
            Patient(name="Uma Refill", age=67, sex="F", chief_complaint="Ran out of blood pressure medication, needs refill", current_esi=5),
            VitalSigns(patient_id="", heart_rate=72, respiratory_rate=14, spo2=98, systolic_bp=135, diastolic_bp=82, temperature=36.7, pain_score=0),
        ),
    ]

    for p, v in cases:
        insert_patient(conn, p)
        v.patient_id = p.id
        insert_vitals(conn, v)

    return cases


def test_score_20_patients(test_db):
    cases = generate_sample_patients(test_db)
    scorer = HybridRiskScorer()
    llm = LLMEngine()

    scored_count = 0
    for p, v in cases[:20]:
        analysis = llm.analyze_complaint(p.chief_complaint, p.age, p.sex)
        # Determine resources based on ESI
        resources = 0 if p.current_esi == 5 else (1 if p.current_esi == 4 else 2)
        result = scorer.score(p, v, analysis, resources_needed=resources)

        assert 1 <= result.esi_level <= 5
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.justification) > 0
        scored_count += 1

    assert scored_count >= 20


def test_ambiguous_case_has_red_flags(test_db):
    patient = Patient(
        name="Ambiguous Female",
        age=52,
        sex="F",
        chief_complaint="epigastric burning, nausea, fatigue, jaw tightness",
    )
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=82,
        respiratory_rate=16,
        spo2=98.0,
        systolic_bp=130,
        diastolic_bp=80,
        temperature=37.0,
    )
    insert_patient(test_db, patient)
    insert_vitals(test_db, vitals)

    llm = LLMEngine()
    scorer = HybridRiskScorer()
    analysis = llm.analyze_complaint(patient.chief_complaint, patient.age, patient.sex)
    result = scorer.score(patient, vitals, analysis, resources_needed=2)

    assert len(result.red_flags) > 0
    assert "ATYPICAL_CARDIAC_FEMALE" in result.red_flags or any("cardiac" in f.lower() for f in result.red_flags)


def test_pediatric_case(test_db):
    patient = Patient(name="Pediatric Infant", age=2.0, sex="M", chief_complaint="High fever and lethargy")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=170,
        respiratory_rate=45,
        spo2=94.0,
        systolic_bp=80,
        diastolic_bp=50,
        temperature=39.5,
    )
    insert_patient(test_db, patient)
    insert_vitals(test_db, vitals)

    scorer = HybridRiskScorer()
    llm = LLMEngine()
    analysis = llm.analyze_complaint(patient.chief_complaint, patient.age, patient.sex)
    result = scorer.score(patient, vitals, analysis, resources_needed=2)

    # Danger zone for toddler triggers ESI 2
    assert result.esi_level == 2


def test_geriatric_case(test_db):
    patient = Patient(name="Geriatric Male", age=82, sex="M", chief_complaint="confused, weakness, lethargic")
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=115,
        respiratory_rate=22,
        spo2=93.0,
        systolic_bp=95,
        diastolic_bp=55,
        temperature=35.6,
    )
    insert_patient(test_db, patient)
    insert_vitals(test_db, vitals)

    scorer = HybridRiskScorer()
    llm = LLMEngine()
    analysis = llm.analyze_complaint(patient.chief_complaint, patient.age, patient.sex)
    result = scorer.score(patient, vitals, analysis, resources_needed=2)

    assert result.esi_level == 2
    assert "GERIATRIC_SEPSIS" in result.red_flags or any("sepsis" in f.lower() for f in result.red_flags)


def test_zero_history_patient(test_db):
    patient = Patient(
        name="Zero History Patient",
        age=30,
        sex="M",
        chief_complaint="Mild ankle sprain",
        medical_history="",
    )
    vitals = VitalSigns(
        patient_id=patient.id,
        heart_rate=72,
        respiratory_rate=14,
        spo2=99.0,
        systolic_bp=118,
        diastolic_bp=76,
        temperature=36.8,
    )
    insert_patient(test_db, patient)
    insert_vitals(test_db, vitals)

    scorer = HybridRiskScorer()
    llm = LLMEngine()
    analysis = llm.analyze_complaint(patient.chief_complaint, patient.age, patient.sex)
    result = scorer.score(patient, vitals, analysis, resources_needed=1)

    assert result.esi_level == 4
    assert result.confidence >= 0.5


def test_override_logged(test_db):
    patient = Patient(name="Override Patient", age=45, sex="F", chief_complaint="headache", current_esi=3)
    insert_patient(test_db, patient)

    entry = AuditEntry(
        patient_id=patient.id,
        clinician_id="RN-Test",
        event_type="OVERRIDDEN",
        ai_esi=3,
        ai_confidence=0.75,
        ai_justification="Stable headache",
        final_esi=2,
        override_reason_code="PATIENT_PAIN_SEVERITY",
        override_note="Patient in extreme agony, suspected thunderclap",
        dwell_seconds=14.5,
        vitals_snapshot={"pain_score": 10},
    )
    insert_audit_log(test_db, entry)

    audit_logs = get_audit_trail(test_db, patient.id)
    assert len(audit_logs) == 1
    logged = audit_logs[0]
    assert logged["event_type"] == "OVERRIDDEN"
    assert logged["final_esi"] == 2
    assert logged["override_reason_code"] == "PATIENT_PAIN_SEVERITY"
    assert logged["override_note"] == "Patient in extreme agony, suspected thunderclap"
    assert logged["dwell_seconds"] == 14.5


def test_surge_reclassification():
    sm = SurgeManager()
    sm.activate()
    test_cases = [
        ("p1", True, 18, True, True, False, "GREEN"),
        ("p2", False, 0, False, False, False, "BLUE"),
        ("p3", False, 35, True, True, False, "RED"),
        ("p4", False, 20, False, True, False, "RED"),
        ("p5", False, 20, True, True, False, "YELLOW"),
    ]

    for pid, walk, rr, pulse, cmd, airway, expected in test_cases:
        cat = sm.start_triage(pid, walk, rr, pulse, cmd, airway)
        assert cat == expected

    stats = sm.get_stats()
    assert stats["GREEN"] == 1
    assert stats["BLUE"] == 1
    assert stats["RED"] == 2
    assert stats["YELLOW"] == 1


def test_queue_ordering(test_db):
    now = datetime.now(timezone.utc)
    p1 = Patient(id="q1", name="ESI 1", age=40, sex="M", arrival_time=now, current_esi=1)
    p2 = Patient(id="q2", name="ESI 2", age=40, sex="M", arrival_time=now, current_esi=2)
    p3 = Patient(id="q3", name="ESI 3 Long Wait", age=40, sex="M", arrival_time=now - timedelta(minutes=60), current_esi=3)
    p4 = Patient(id="q4", name="ESI 3 Short Wait", age=40, sex="M", arrival_time=now - timedelta(minutes=5), current_esi=3)
    p5 = Patient(id="q5", name="ESI 5", age=40, sex="M", arrival_time=now, current_esi=5)

    for p in [p1, p2, p3, p4, p5]:
        insert_patient(test_db, p)
        v = VitalSigns(patient_id=p.id, heart_rate=75, respiratory_rate=16, spo2=98, systolic_bp=120, diastolic_bp=80, temperature=37.0)
        insert_vitals(test_db, v)

    ranked = get_ranked_queue(test_db)
    ids = [p["id"] for p in ranked]

    # ESI 1 (priority ~1000) > ESI 2 (~500) > ESI 3 Long Wait (200 + 60*2 + deterioration bonus) > ESI 3 Short Wait > ESI 5
    assert ids[0] == "q1"
    assert ids[1] == "q2"
    assert ids.index("q3") < ids.index("q4")
    assert ids[-1] == "q5"
