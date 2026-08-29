from datetime import datetime, timezone
import sqlite3
import config
from src.database import get_all_waiting_patients, get_latest_vitals


def calculate_priority(esi_level: int, wait_minutes: float, deterioration_bonus: float = 0.0) -> float:
    base = config.ACUITY_BASE.get(esi_level, 50)
    factor = config.ACUITY_WAIT_FACTOR.get(esi_level, 0.5)
    return round(base + (wait_minutes * factor) + deterioration_bonus, 2)


def parse_datetime(val: str | datetime) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def get_ranked_queue(conn: sqlite3.Connection) -> list[dict]:
    patients = get_all_waiting_patients(conn)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    ranked = []

    for p in patients:
        pid = p["id"]
        arrival = parse_datetime(p.get("arrival_time", now))
        wait_minutes = max(0.0, (now - arrival).total_seconds() / 60.0)

        # Get latest triage result or fallback to current_esi
        esi_level = p.get("current_esi")
        cursor.execute(
            "SELECT * FROM triage_results WHERE patient_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (pid,),
        )
        triage_row = cursor.fetchone()
        if triage_row:
            esi_level = triage_row["esi_level"]

        if esi_level is None:
            esi_level = 3

        vitals = get_latest_vitals(conn, pid)

        # Calculate deterioration bonus if overdue
        threshold = config.DETERIORATION_THRESHOLDS_MIN.get(esi_level, 120)
        overdue = max(0.0, wait_minutes - threshold)
        deterioration_bonus = overdue * 2.0 if overdue > 0 else 0.0

        priority = calculate_priority(esi_level, wait_minutes, deterioration_bonus)

        p_info = dict(p)
        p_info["wait_minutes"] = round(wait_minutes, 1)
        p_info["priority_score"] = priority
        p_info["esi_level"] = esi_level
        if vitals:
            p_info["vitals"] = vitals
        if triage_row:
            p_info["triage_result"] = dict(triage_row)

        ranked.append(p_info)

    # Sort descending by priority
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked


def check_deterioration_alerts(conn: sqlite3.Connection) -> list[dict]:
    patients = get_all_waiting_patients(conn)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    alerts = []

    for p in patients:
        pid = p["id"]
        arrival = parse_datetime(p.get("arrival_time", now))
        wait_minutes = max(0.0, (now - arrival).total_seconds() / 60.0)

        esi_level = p.get("current_esi")
        cursor.execute(
            "SELECT esi_level FROM triage_results WHERE patient_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (pid,),
        )
        triage_row = cursor.fetchone()
        if triage_row:
            esi_level = triage_row["esi_level"]

        if esi_level is None:
            esi_level = 3

        threshold = config.DETERIORATION_THRESHOLDS_MIN.get(esi_level, 120)
        if wait_minutes > threshold:
            overdue_minutes = wait_minutes - threshold
            alerts.append({
                "patient_id": pid,
                "name": p.get("name", "Unknown"),
                "esi_level": esi_level,
                "wait_minutes": round(wait_minutes, 1),
                "threshold_minutes": threshold,
                "overdue_minutes": round(overdue_minutes, 1),
            })

    # Sort by ESI urgency (1 first), then overdue minutes descending
    alerts.sort(key=lambda a: (a["esi_level"], -a["overdue_minutes"]))
    return alerts
