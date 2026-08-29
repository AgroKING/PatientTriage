import pytest
from src.clinical_rules import (
    calculate_news2,
    calculate_shock_index,
    check_danger_zone,
    check_red_flags,
    esi_decision_tree,
    get_age_group,
    get_pediatric_sbp_threshold,
)
from src.models import Patient, VitalSigns


def make_vitals(
    patient_id: str = "p1",
    heart_rate: int = 75,
    respiratory_rate: int = 16,
    spo2: float = 98.0,
    systolic_bp: int = 120,
    diastolic_bp: int = 80,
    temperature: float = 37.0,
    pain_score: int = 0,
    consciousness: str = "A",
    supplemental_o2: bool = False,
) -> VitalSigns:
    return VitalSigns(
        patient_id=patient_id,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        spo2=spo2,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        temperature=temperature,
        pain_score=pain_score,
        consciousness=consciousness,
        supplemental_o2=supplemental_o2,
    )


def test_age_group_mapping():
    assert get_age_group(0.01) == "NEONATE"
    assert get_age_group(0.1) == "INFANT"
    assert get_age_group(1.0) == "TODDLER"
    assert get_age_group(5) == "CHILD"
    assert get_age_group(30) == "ADULT"
    assert get_age_group(70) == "GERIATRIC"


def test_pediatric_sbp():
    assert get_pediatric_sbp_threshold(4) == 78
    assert get_pediatric_sbp_threshold(6) == 82


def test_danger_zone_adult_tachycardia():
    v = make_vitals(heart_rate=110)
    is_danger, triggers = check_danger_zone(v, 30.0)
    assert is_danger is True
    assert any("HR" in t for t in triggers)


def test_danger_zone_adult_normal():
    v = make_vitals(heart_rate=80, respiratory_rate=16, spo2=98, systolic_bp=120, temperature=37.0)
    is_danger, triggers = check_danger_zone(v, 30.0)
    assert is_danger is False
    assert len(triggers) == 0


def test_danger_zone_geriatric_hypothermia():
    v = make_vitals(temperature=35.5)
    is_danger, triggers = check_danger_zone(v, 70.0)
    assert is_danger is True
    assert any("Temp" in t for t in triggers)


def test_danger_zone_neonate_fever():
    v = make_vitals(heart_rate=140, respiratory_rate=35, systolic_bp=65, temperature=38.5)
    is_danger, triggers = check_danger_zone(v, 0.02)
    assert is_danger is True
    assert any("Temp" in t for t in triggers)


def test_news2_all_normal():
    v = make_vitals(
        heart_rate=70,
        respiratory_rate=15,
        spo2=98,
        systolic_bp=120,
        temperature=37.0,
        consciousness="A",
        supplemental_o2=False,
    )
    score, breakdown = calculate_news2(v)
    assert score == 0


def test_news2_high_risk():
    v = make_vitals(
        heart_rate=135,
        respiratory_rate=26,
        spo2=90,
        systolic_bp=85,
        temperature=39.5,
        consciousness="V",
        supplemental_o2=True,
    )
    score, breakdown = calculate_news2(v)
    assert score >= 7


def test_shock_index_normal():
    si, flagged = calculate_shock_index(70, 120)
    assert si == 0.58
    assert flagged is False


def test_shock_index_high():
    si, flagged = calculate_shock_index(110, 95)
    assert si == 1.16
    assert flagged is True


def test_red_flag_atypical_cardiac():
    v = make_vitals()
    flags = check_red_flags("Patient reports jaw pain and nausea", 55.0, "F", v)
    assert "ATYPICAL_CARDIAC_FEMALE" in flags


def test_red_flag_geriatric_sepsis():
    v = make_vitals(temperature=35.5)
    flags = check_red_flags("Patient is confused and lethargic", 75.0, "M", v)
    assert "GERIATRIC_SEPSIS" in flags


def test_red_flag_silent_mi():
    v = make_vitals()
    flags = check_red_flags(
        "profuse sweating and dyspnea",
        60.0,
        "M",
        v,
        has_diabetes=True,
    )
    assert "SILENT_MI_DIABETIC" in flags


def test_esi_level_1():
    patient = Patient(name="John Doe", age=45, sex="M")
    v = make_vitals(consciousness="U")
    esi, just = esi_decision_tree(patient, v, resources_needed=2, danger_zone_result=(False, []), red_flags=[])
    assert esi == 1


def test_esi_level_2_pain():
    patient = Patient(name="Jane Doe", age=30, sex="F")
    v = make_vitals(pain_score=8)
    esi, just = esi_decision_tree(patient, v, resources_needed=1, danger_zone_result=(False, []), red_flags=[])
    assert esi == 2


def test_esi_level_5():
    patient = Patient(name="Bob", age=25, sex="M")
    v = make_vitals()
    esi, just = esi_decision_tree(patient, v, resources_needed=0, danger_zone_result=(False, []), red_flags=[])
    assert esi == 5


def test_esi_level_4():
    patient = Patient(name="Alice", age=28, sex="F")
    v = make_vitals()
    esi, just = esi_decision_tree(patient, v, resources_needed=1, danger_zone_result=(False, []), red_flags=[])
    assert esi == 4


def test_esi_level_3():
    patient = Patient(name="Charlie", age=35, sex="M")
    v = make_vitals()
    esi, just = esi_decision_tree(patient, v, resources_needed=2, danger_zone_result=(False, []), red_flags=[])
    assert esi == 3


def test_esi_level_2_danger_zone():
    patient = Patient(name="David", age=40, sex="M")
    v = make_vitals(heart_rate=115)
    danger = check_danger_zone(v, patient.age)
    esi, just = esi_decision_tree(patient, v, resources_needed=2, danger_zone_result=danger, red_flags=[])
    assert esi == 2
