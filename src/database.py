import json
import os
import sqlite3
from src.models import AuditEntry, Patient, TriageResult, VitalSigns


def init_db(db_path: str) -> sqlite3.Connection:
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age REAL NOT NULL,
        sex TEXT NOT NULL,
        arrival_time TEXT NOT NULL,
        chief_complaint TEXT DEFAULT '',
        medical_history TEXT DEFAULT '',
        status TEXT DEFAULT 'WAITING',
        current_esi INTEGER
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vitals_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        heart_rate INTEGER,
        respiratory_rate INTEGER,
        spo2 REAL,
        systolic_bp INTEGER,
        diastolic_bp INTEGER,
        temperature REAL,
        pain_score INTEGER,
        consciousness TEXT DEFAULT 'A',
        supplemental_o2 INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS triage_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        esi_level INTEGER NOT NULL,
        news2_score INTEGER,
        confidence REAL,
        justification TEXT,
        red_flags TEXT,
        is_override INTEGER DEFAULT 0,
        override_reason TEXT,
        override_note TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        clinician_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        ai_esi INTEGER,
        ai_confidence REAL,
        ai_justification TEXT,
        final_esi INTEGER,
        override_reason_code TEXT,
        override_note TEXT,
        dwell_seconds REAL,
        vitals_snapshot TEXT
    );
    """)

    conn.commit()
    return conn


def insert_patient(conn: sqlite3.Connection, patient: Patient) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO patients (id, name, age, sex, arrival_time, chief_complaint, medical_history, status, current_esi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient.id,
            patient.name,
            patient.age,
            patient.sex,
            patient.arrival_time.isoformat() if hasattr(patient.arrival_time, "isoformat") else str(patient.arrival_time),
            patient.chief_complaint,
            patient.medical_history,
            patient.status,
            patient.current_esi,
        ),
    )
    conn.commit()


def insert_vitals(conn: sqlite3.Connection, vitals: VitalSigns) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO vitals_history (patient_id, timestamp, heart_rate, respiratory_rate, spo2, systolic_bp, diastolic_bp, temperature, pain_score, consciousness, supplemental_o2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vitals.patient_id,
            vitals.timestamp.isoformat() if hasattr(vitals.timestamp, "isoformat") else str(vitals.timestamp),
            vitals.heart_rate,
            vitals.respiratory_rate,
            vitals.spo2,
            vitals.systolic_bp,
            vitals.diastolic_bp,
            vitals.temperature,
            vitals.pain_score,
            vitals.consciousness,
            1 if vitals.supplemental_o2 else 0,
        ),
    )
    conn.commit()


def insert_triage_result(conn: sqlite3.Connection, result: TriageResult) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO triage_results (patient_id, timestamp, esi_level, news2_score, confidence, justification, red_flags, is_override, override_reason, override_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.patient_id,
            result.timestamp.isoformat() if hasattr(result.timestamp, "isoformat") else str(result.timestamp),
            result.esi_level,
            result.news2_score,
            result.confidence,
            result.justification,
            json.dumps(result.red_flags),
            1 if result.is_override else 0,
            result.override_reason,
            result.override_note,
        ),
    )
    conn.commit()


def insert_audit_log(conn: sqlite3.Connection, entry: AuditEntry) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_logs (id, timestamp, patient_id, clinician_id, event_type, ai_esi, ai_confidence, ai_justification, final_esi, override_reason_code, override_note, dwell_seconds, vitals_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.id,
            entry.timestamp.isoformat() if hasattr(entry.timestamp, "isoformat") else str(entry.timestamp),
            entry.patient_id,
            entry.clinician_id,
            entry.event_type,
            entry.ai_esi,
            entry.ai_confidence,
            entry.ai_justification,
            entry.final_esi,
            entry.override_reason_code,
            entry.override_note,
            entry.dwell_seconds,
            json.dumps(entry.vitals_snapshot),
        ),
    )
    conn.commit()


def get_patient(conn: sqlite3.Connection, patient_id: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_latest_vitals(conn: sqlite3.Connection, patient_id: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM vitals_history WHERE patient_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
        (patient_id,),
    )
    row = cursor.fetchone()
    if row:
        d = dict(row)
        d["supplemental_o2"] = bool(d.get("supplemental_o2", 0))
        return d
    return None


def get_all_waiting_patients(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE status = 'WAITING'")
    return [dict(row) for row in cursor.fetchall()]


def update_patient_status(conn: sqlite3.Connection, patient_id: str, status: str) -> None:
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET status = ? WHERE id = ?", (status, patient_id))
    conn.commit()


def update_patient_esi(conn: sqlite3.Connection, patient_id: str, esi: int) -> None:
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET current_esi = ? WHERE id = ?", (esi, patient_id))
    conn.commit()


def get_audit_trail(conn: sqlite3.Connection, patient_id: str | None = None) -> list[dict]:
    cursor = conn.cursor()
    if patient_id:
        cursor.execute("SELECT * FROM audit_logs WHERE patient_id = ? ORDER BY timestamp DESC", (patient_id,))
    else:
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("vitals_snapshot"), str):
            try:
                d["vitals_snapshot"] = json.loads(d["vitals_snapshot"])
            except Exception:
                pass
        results.append(d)
    return results


def get_all_patients(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients ORDER BY arrival_time DESC")
    return [dict(row) for row in cursor.fetchall()]
