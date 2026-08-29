from datetime import datetime, timedelta, timezone
import pytest
from src.database import init_db, insert_patient
from src.models import Patient
from src.queue_manager import calculate_priority, check_deterioration_alerts, get_ranked_queue
from src.surge_manager import SurgeManager


def test_esi1_ranks_above_esi2():
    p1 = calculate_priority(1, wait_minutes=0)
    p2 = calculate_priority(2, wait_minutes=0)
    assert p1 > p2


def test_wait_time_increases_priority():
    p_short = calculate_priority(3, wait_minutes=5)
    p_long = calculate_priority(3, wait_minutes=60)
    assert p_long > p_short


def test_esi2_alert_at_11_min(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)

    arrival = datetime.now(timezone.utc) - timedelta(minutes=11)
    patient = Patient(
        id="p_esi2",
        name="ESI2 Patient",
        age=50,
        sex="M",
        arrival_time=arrival,
        current_esi=2,
    )
    insert_patient(conn, patient)

    alerts = check_deterioration_alerts(conn)
    assert len(alerts) == 1
    assert alerts[0]["patient_id"] == "p_esi2"
    assert alerts[0]["esi_level"] == 2


def test_esi3_no_alert_at_20_min(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)

    arrival = datetime.now(timezone.utc) - timedelta(minutes=20)
    patient = Patient(
        id="p_esi3",
        name="ESI3 Patient",
        age=30,
        sex="F",
        arrival_time=arrival,
        current_esi=3,
    )
    insert_patient(conn, patient)

    alerts = check_deterioration_alerts(conn)
    assert len(alerts) == 0


def test_esi3_alert_at_31_min(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)

    arrival = datetime.now(timezone.utc) - timedelta(minutes=31)
    patient = Patient(
        id="p_esi3_late",
        name="ESI3 Late Patient",
        age=30,
        sex="F",
        arrival_time=arrival,
        current_esi=3,
    )
    insert_patient(conn, patient)

    alerts = check_deterioration_alerts(conn)
    assert len(alerts) == 1
    assert alerts[0]["patient_id"] == "p_esi3_late"


def test_start_walking_is_green():
    sm = SurgeManager()
    sm.activate()
    cat = sm.start_triage(
        patient_id="p1",
        can_walk=True,
        respiratory_rate=20,
        has_radial_pulse=True,
        follows_commands=True,
        breathing_after_airway=False,
    )
    assert cat == "GREEN"


def test_start_apneic_no_recovery_is_blue():
    sm = SurgeManager()
    sm.activate()
    cat = sm.start_triage(
        patient_id="p2",
        can_walk=False,
        respiratory_rate=0,
        has_radial_pulse=False,
        follows_commands=False,
        breathing_after_airway=False,
    )
    assert cat == "BLUE"


def test_start_high_rr_is_red():
    sm = SurgeManager()
    sm.activate()
    cat = sm.start_triage(
        patient_id="p3",
        can_walk=False,
        respiratory_rate=35,
        has_radial_pulse=True,
        follows_commands=True,
        breathing_after_airway=False,
    )
    assert cat == "RED"


def test_start_no_pulse_is_red():
    sm = SurgeManager()
    sm.activate()
    cat = sm.start_triage(
        patient_id="p4",
        can_walk=False,
        respiratory_rate=22,
        has_radial_pulse=False,
        follows_commands=True,
        breathing_after_airway=False,
    )
    assert cat == "RED"


def test_start_follows_commands_is_yellow():
    sm = SurgeManager()
    sm.activate()
    cat = sm.start_triage(
        patient_id="p5",
        can_walk=False,
        respiratory_rate=20,
        has_radial_pulse=True,
        follows_commands=True,
        breathing_after_airway=False,
    )
    assert cat == "YELLOW"
