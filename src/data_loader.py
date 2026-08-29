import sqlite3
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from src.database import get_latest_vitals, insert_patient, insert_vitals
from src.models import Patient, VitalSigns


KNOWN_COMORBIDITIES = [
    "hypertension", "diabetes", "hyperlipidemia", "coronary_artery_disease",
    "heart_failure", "atrial_fibrillation", "copd", "asthma", "ckd",
    "end_stage_renal_disease", "stroke_tia", "dementia", "cancer",
    "depression", "anxiety", "cirrhosis", "gerd", "osteoarthritis",
    "obesity", "substance_abuse", "hiv", "rheumatoid_arthritis",
    "epilepsy", "peripheral_vascular_disease", "thyroid_disorder"
]


def load_triagegeist(conn: sqlite3.Connection, csv_path: str, limit: int | None = None) -> int:
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)

    count = 0
    for _, row in df.iterrows():
        patient_id = str(row.get("patient_id", f"TG-{count+1:06d}"))
        age = float(row.get("age", 45.0))
        raw_sex = str(row.get("sex", "M")).upper()
        sex = "F" if raw_sex.startswith("F") or raw_sex == "1" or raw_sex == "FEMALE" else "M"
        chief_complaint = str(row.get("chief_complaint_raw", row.get("chief_complaint", "")))
        if pd.isna(chief_complaint) or chief_complaint.lower() == "nan":
            chief_complaint = ""

        # Extract comorbidities
        active_comorbidities = []
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in KNOWN_COMORBIDITIES or col_lower.startswith("cci_") or col_lower.startswith("comorbidity_"):
                val = row[col]
                if pd.notna(val) and (val == 1 or val is True or str(val).strip() in ("1", "true", "True")):
                    clean_name = col_lower.replace("cci_", "").replace("comorbidity_", "").replace("_", " ")
                    active_comorbidities.append(clean_name)

        medical_history = ", ".join(active_comorbidities)

        current_esi = None
        if "triage_acuity" in row and pd.notna(row["triage_acuity"]):
            try:
                current_esi = int(row["triage_acuity"])
            except (ValueError, TypeError):
                current_esi = None
        elif "esi" in row and pd.notna(row["esi"]):
            try:
                current_esi = int(row["esi"])
            except (ValueError, TypeError):
                current_esi = None

        name = str(row.get("name", f"Patient {patient_id}"))

        patient = Patient(
            id=patient_id,
            name=name,
            age=age,
            sex=sex,
            chief_complaint=chief_complaint,
            medical_history=medical_history,
            status="WAITING",
            current_esi=current_esi,
        )
        insert_patient(conn, patient)

        hr = int(row.get("heart_rate", 75)) if pd.notna(row.get("heart_rate")) else 75
        rr = int(row.get("respiratory_rate", 16)) if pd.notna(row.get("respiratory_rate")) else 16
        spo2 = float(row.get("spo2", 98.0)) if pd.notna(row.get("spo2")) else 98.0
        sbp = int(row.get("systolic_bp", 120)) if pd.notna(row.get("systolic_bp")) else 120
        dbp = int(row.get("diastolic_bp", 80)) if pd.notna(row.get("diastolic_bp")) else 80
        temp = float(row.get("temperature_c", row.get("temperature", 37.0))) if pd.notna(row.get("temperature_c", row.get("temperature", None))) else 37.0
        pain = int(row.get("pain_score", 0)) if pd.notna(row.get("pain_score")) else 0
        consciousness = str(row.get("consciousness", "A")).upper()
        if consciousness not in ("A", "V", "P", "U"):
            consciousness = "A"
        supp_o2 = bool(row.get("supplemental_o2", False))

        vitals = VitalSigns(
            patient_id=patient_id,
            heart_rate=hr,
            respiratory_rate=rr,
            spo2=spo2,
            systolic_bp=sbp,
            diastolic_bp=dbp,
            temperature=temp,
            pain_score=pain,
            consciousness=consciousness,
            supplemental_o2=supp_o2,
        )
        insert_vitals(conn, vitals)
        count += 1

    return count


def select_demo_cases(conn: sqlite3.Connection, n: int = 25) -> list[dict]:
    cursor = conn.cursor()
    selected_ids: set[str] = set()
    cases: list[dict] = []

    def fetch_cases(query: str, params: tuple = (), target_count: int = 1) -> None:
        cursor.execute(query, params)
        for r in cursor.fetchall():
            row_dict = dict(r)
            if row_dict["id"] not in selected_ids:
                selected_ids.add(row_dict["id"])
                vitals = get_latest_vitals(conn, row_dict["id"])
                if vitals:
                    row_dict.update(vitals)
                cases.append(row_dict)
                if len([c for c in cases if c.get("current_esi") == row_dict.get("current_esi")]) >= target_count:
                    break

    # ESI 1 cases (2)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 1 LIMIT 10", (), 2)
    # ESI 2 cases (5) - include female age>=40 with cardiac complaint and geriatric
    fetch_cases("SELECT * FROM patients WHERE current_esi = 2 AND sex = 'F' AND age >= 40 AND (chief_complaint LIKE '%jaw%' OR chief_complaint LIKE '%nausea%' OR chief_complaint LIKE '%chest%' OR chief_complaint LIKE '%epigastric%' OR chief_complaint LIKE '%fatigue%') LIMIT 5", (), 1)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 2 AND age >= 65 LIMIT 5", (), 2)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 2 LIMIT 10", (), 5)
    # ESI 3 cases (8)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 3 LIMIT 15", (), 8)
    # ESI 4 cases (6)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 4 LIMIT 15", (), 6)
    # ESI 5 cases (4)
    fetch_cases("SELECT * FROM patients WHERE current_esi = 5 LIMIT 10", (), 4)

    # Pediatric cases (at least 2)
    fetch_cases("SELECT * FROM patients WHERE age < 8 LIMIT 5", (), 2)
    # Geriatric cases (at least 2)
    fetch_cases("SELECT * FROM patients WHERE age >= 65 LIMIT 5", (), 2)
    # Zero-history cases (at least 3)
    fetch_cases("SELECT * FROM patients WHERE medical_history = '' OR medical_history IS NULL LIMIT 10", (), 3)

    # If still fewer than requested or needed, fill with general patients
    if len(cases) < n:
        cursor.execute("SELECT * FROM patients LIMIT ?", (n * 2,))
        for r in cursor.fetchall():
            row_dict = dict(r)
            if row_dict["id"] not in selected_ids:
                selected_ids.add(row_dict["id"])
                vitals = get_latest_vitals(conn, row_dict["id"])
                if vitals:
                    row_dict.update(vitals)
                cases.append(row_dict)
                if len(cases) >= n:
                    break

    return cases[:n]


def get_training_data(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.Series]:
    query = """
    SELECT
        p.age,
        CASE WHEN p.sex = 'F' THEN 1 ELSE 0 END as sex_encoded,
        v.heart_rate,
        v.respiratory_rate,
        v.spo2,
        v.systolic_bp,
        v.diastolic_bp,
        v.temperature,
        v.pain_score,
        p.current_esi as triage_acuity
    FROM patients p
    INNER JOIN vitals_history v ON p.id = v.patient_id
    WHERE p.current_esi IS NOT NULL
      AND v.heart_rate IS NOT NULL
      AND v.respiratory_rate IS NOT NULL
      AND v.spo2 IS NOT NULL
      AND v.systolic_bp IS NOT NULL
      AND v.diastolic_bp IS NOT NULL
      AND v.temperature IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    df = df.dropna()

    feature_cols = [
        "age", "sex_encoded", "heart_rate", "respiratory_rate",
        "spo2", "systolic_bp", "diastolic_bp", "temperature", "pain_score"
    ]
    X = df[feature_cols]
    y = df["triage_acuity"].astype(int)
    return X, y


def seed_demo_patients(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] > 0:
        return

    now = datetime.now(timezone.utc)
    cases = [
        (
            Patient(id="DEMO-001", name="Alice Shock", age=50, sex="F", chief_complaint="Unresponsive and cold to touch", current_esi=1, arrival_time=now),
            VitalSigns(patient_id="DEMO-001", heart_rate=35, respiratory_rate=8, spo2=75, systolic_bp=55, diastolic_bp=30, temperature=34.5, consciousness="U")
        ),
        (
            Patient(id="DEMO-002", name="Bob Trauma", age=28, sex="M", chief_complaint="MVA crush injury severe respiratory distress", current_esi=1, arrival_time=now),
            VitalSigns(patient_id="DEMO-002", heart_rate=145, respiratory_rate=38, spo2=82, systolic_bp=80, diastolic_bp=50, temperature=36.2, consciousness="P")
        ),
        (
            Patient(id="DEMO-003", name="Carol Cardiac", age=54, sex="F", chief_complaint="Jaw pain, epigastric discomfort, persistent nausea", current_esi=2, arrival_time=now - timedelta(minutes=5)),
            VitalSigns(patient_id="DEMO-003", heart_rate=88, respiratory_rate=18, spo2=97, systolic_bp=135, diastolic_bp=85, temperature=36.8, pain_score=6)
        ),
        (
            Patient(id="DEMO-004", name="David Sepsis", age=78, sex="M", chief_complaint="Confused, lethargic, not acting right", current_esi=2, arrival_time=now - timedelta(minutes=15)),
            VitalSigns(patient_id="DEMO-004", heart_rate=112, respiratory_rate=24, spo2=93, systolic_bp=95, diastolic_bp=55, temperature=35.4, consciousness="V")
        ),
        (
            Patient(id="DEMO-005", name="Eva Peds", age=4, sex="F", chief_complaint="High fever and rapid breathing", current_esi=2, arrival_time=now - timedelta(minutes=12)),
            VitalSigns(patient_id="DEMO-005", heart_rate=165, respiratory_rate=36, spo2=94, systolic_bp=85, diastolic_bp=55, temperature=39.2, pain_score=7)
        ),
        (
            Patient(id="DEMO-006", name="Frank Pain", age=35, sex="M", chief_complaint="Acute renal colic severe flank pain", current_esi=2, arrival_time=now - timedelta(minutes=8)),
            VitalSigns(patient_id="DEMO-006", heart_rate=95, respiratory_rate=18, spo2=98, systolic_bp=140, diastolic_bp=90, temperature=37.0, pain_score=9)
        ),
        (
            Patient(id="DEMO-007", name="Grace Diabetic", age=62, sex="F", chief_complaint="Profuse sweating, sudden dyspnea, extreme weakness", medical_history="Type 2 diabetes", current_esi=2, arrival_time=now - timedelta(minutes=2)),
            VitalSigns(patient_id="DEMO-007", heart_rate=105, respiratory_rate=22, spo2=93, systolic_bp=130, diastolic_bp=82, temperature=36.9, pain_score=2)
        ),
        (
            Patient(id="DEMO-008", name="Henry Abdo", age=42, sex="M", chief_complaint="Right lower quadrant abdominal pain for 6 hours", current_esi=3, arrival_time=now - timedelta(minutes=45)),
            VitalSigns(patient_id="DEMO-008", heart_rate=80, respiratory_rate=16, spo2=99, systolic_bp=125, diastolic_bp=80, temperature=37.2, pain_score=4)
        ),
        (
            Patient(id="DEMO-009", name="Iris Headache", age=31, sex="F", chief_complaint="Moderate migraine with light sensitivity", current_esi=3, arrival_time=now - timedelta(minutes=35)),
            VitalSigns(patient_id="DEMO-009", heart_rate=76, respiratory_rate=15, spo2=98, systolic_bp=118, diastolic_bp=75, temperature=36.8, pain_score=5)
        ),
        (
            Patient(id="DEMO-010", name="Jack Fracture", age=22, sex="M", chief_complaint="Closed wrist deformity after skateboard fall", current_esi=3, arrival_time=now - timedelta(minutes=25)),
            VitalSigns(patient_id="DEMO-010", heart_rate=84, respiratory_rate=16, spo2=99, systolic_bp=128, diastolic_bp=82, temperature=36.7, pain_score=6)
        ),
        (
            Patient(id="DEMO-011", name="Karen Asthma", age=29, sex="F", chief_complaint="Mild asthma flare responsive to inhaler", medical_history="Asthma", current_esi=3, arrival_time=now - timedelta(minutes=22)),
            VitalSigns(patient_id="DEMO-011", heart_rate=88, respiratory_rate=20, spo2=96, systolic_bp=120, diastolic_bp=80, temperature=37.0, pain_score=2)
        ),
        (
            Patient(id="DEMO-012", name="Leo Vomit", age=50, sex="M", chief_complaint="Nausea and vomiting x 2 days", current_esi=3, arrival_time=now - timedelta(minutes=18)),
            VitalSigns(patient_id="DEMO-012", heart_rate=85, respiratory_rate=16, spo2=98, systolic_bp=115, diastolic_bp=75, temperature=37.3, pain_score=3)
        ),
        (
            Patient(id="DEMO-013", name="Mona Cellulitis", age=60, sex="F", chief_complaint="Redness and swelling in right lower leg", current_esi=3, arrival_time=now - timedelta(minutes=14)),
            VitalSigns(patient_id="DEMO-013", heart_rate=82, respiratory_rate=16, spo2=98, systolic_bp=130, diastolic_bp=80, temperature=37.6, pain_score=4)
        ),
        (
            Patient(id="DEMO-014", name="Ned ZeroHist", age=38, sex="M", chief_complaint="Persistent abdominal cramps and nausea", medical_history="", current_esi=3, arrival_time=now - timedelta(minutes=10)),
            VitalSigns(patient_id="DEMO-014", heart_rate=78, respiratory_rate=16, spo2=98, systolic_bp=120, diastolic_bp=80, temperature=37.0, pain_score=3)
        ),
        (
            Patient(id="DEMO-015", name="Olivia UTI", age=26, sex="F", chief_complaint="Dysuria and urinary frequency", current_esi=3, arrival_time=now - timedelta(minutes=60)),
            VitalSigns(patient_id="DEMO-015", heart_rate=74, respiratory_rate=14, spo2=99, systolic_bp=110, diastolic_bp=70, temperature=37.1, pain_score=3)
        ),
        (
            Patient(id="DEMO-016", name="Paul Cut", age=19, sex="M", chief_complaint="Clean finger laceration from kitchen knife", current_esi=4, arrival_time=now - timedelta(minutes=130)),
            VitalSigns(patient_id="DEMO-016", heart_rate=72, respiratory_rate=14, spo2=99, systolic_bp=118, diastolic_bp=76, temperature=36.7, pain_score=2)
        ),
        (
            Patient(id="DEMO-017", name="Quinn Ankle", age=25, sex="F", chief_complaint="Twisted ankle while jogging", current_esi=4, arrival_time=now - timedelta(minutes=80)),
            VitalSigns(patient_id="DEMO-017", heart_rate=70, respiratory_rate=14, spo2=99, systolic_bp=116, diastolic_bp=74, temperature=36.6, pain_score=3)
        ),
        (
            Patient(id="DEMO-018", name="Rita Ear", age=6, sex="F", chief_complaint="Left ear pain and discharge", current_esi=4, arrival_time=now - timedelta(minutes=40)),
            VitalSigns(patient_id="DEMO-018", heart_rate=90, respiratory_rate=20, spo2=99, systolic_bp=98, diastolic_bp=62, temperature=37.5, pain_score=3)
        ),
        (
            Patient(id="DEMO-019", name="Sam Rash", age=45, sex="M", chief_complaint="Localized poison ivy rash on forearm", current_esi=4, arrival_time=now - timedelta(minutes=10)),
            VitalSigns(patient_id="DEMO-019", heart_rate=68, respiratory_rate=14, spo2=99, systolic_bp=122, diastolic_bp=78, temperature=36.8, pain_score=1)
        ),
        (
            Patient(id="DEMO-020", name="Tina Suture", age=33, sex="F", chief_complaint="Suture removal from healed wound", current_esi=5, arrival_time=now - timedelta(minutes=250)),
            VitalSigns(patient_id="DEMO-020", heart_rate=65, respiratory_rate=12, spo2=99, systolic_bp=114, diastolic_bp=72, temperature=36.6, pain_score=0)
        ),
        (
            Patient(id="DEMO-021", name="Uma Refill", age=67, sex="F", chief_complaint="Ran out of blood pressure medication, needs refill", current_esi=5, arrival_time=now - timedelta(minutes=120)),
            VitalSigns(patient_id="DEMO-021", heart_rate=72, respiratory_rate=14, spo2=98, systolic_bp=135, diastolic_bp=82, temperature=36.7, pain_score=0)
        ),
    ]

    for p, v in cases:
        insert_patient(conn, p)
        insert_vitals(conn, v)

