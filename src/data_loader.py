import sqlite3
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
