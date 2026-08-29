import time
import streamlit as st
import config
from src.database import (
    get_all_patients,
    get_latest_vitals,
    get_patient,
    init_db,
    insert_audit_log,
    insert_patient,
    insert_triage_result,
    insert_vitals,
    update_patient_esi,
)
from src.data_loader import select_demo_cases
from src.llm_engine import LLMEngine
from src.models import AuditEntry, Patient, VitalSigns
from src.risk_scorer import HybridRiskScorer

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)

st.title("📋 Patient Intake & AI Triage Scoring")

mode = st.radio("Select Intake Mode", ["Manual Entry", "Load from Dataset"], horizontal=True)

llm = LLMEngine()
scorer = HybridRiskScorer()

patient_data = {}
vitals_data = {}

if mode == "Load from Dataset":
    all_p = get_all_patients(conn)
    if not all_p:
        st.info("No patients found in database. Using sample cases or load dataset.")
        demo_cases = select_demo_cases(conn, n=25)
    else:
        demo_cases = all_p

    options = {
        f"{p.get('name', 'Patient')} ({p.get('id')}) - ESI {p.get('current_esi', '?')}": p
        for p in demo_cases
    }

    if options:
        selected_label = st.selectbox("Select Patient Record", list(options.keys()))
        selected_p = options[selected_label]
        patient_id = selected_p["id"]
        v_latest = get_latest_vitals(conn, patient_id) or {}

        patient_data = {
            "name": selected_p.get("name", ""),
            "age": float(selected_p.get("age", 45.0)),
            "sex": selected_p.get("sex", "M"),
            "chief_complaint": selected_p.get("chief_complaint", ""),
            "medical_history": selected_p.get("medical_history", ""),
        }
        vitals_data = {
            "heart_rate": int(v_latest.get("heart_rate", 75)),
            "respiratory_rate": int(v_latest.get("respiratory_rate", 16)),
            "spo2": float(v_latest.get("spo2", 98.0)),
            "systolic_bp": int(v_latest.get("systolic_bp", 120)),
            "diastolic_bp": int(v_latest.get("diastolic_bp", 80)),
            "temperature": float(v_latest.get("temperature", 37.0)),
            "pain_score": int(v_latest.get("pain_score", 0)),
            "consciousness": v_latest.get("consciousness", "A"),
            "supplemental_o2": bool(v_latest.get("supplemental_o2", False)),
        }
    else:
        st.warning("Database empty. Please switch to Manual Entry or populate data.")

# Intake Form
with st.form("triage_intake_form"):
    st.subheader("1. Patient Demographics & Vitals")
    col1, col2, col3 = st.columns(3)

    with col1:
        patient_name = st.text_input("Patient Full Name", value=patient_data.get("name", "Jane Doe"))
        patient_age = st.number_input("Age (years)", min_value=0.01, max_value=120.0, value=patient_data.get("age", 45.0), step=1.0)
        sex_idx = 1 if patient_data.get("sex", "M") == "F" else 0
        patient_sex = st.selectbox("Sex", ["M", "F"], index=sex_idx)
        avpu_options = ["A", "V", "P", "U"]
        cur_avpu = vitals_data.get("consciousness", "A")
        avpu_idx = avpu_options.index(cur_avpu) if cur_avpu in avpu_options else 0
        consciousness = st.selectbox("Consciousness (AVPU)", avpu_options, index=avpu_idx, help="A=Alert, V=Voice, P=Pain, U=Unresponsive")

    with col2:
        heart_rate = st.number_input("Heart Rate (bpm)", min_value=10, max_value=280, value=vitals_data.get("heart_rate", 78))
        respiratory_rate = st.number_input("Respiratory Rate (breaths/min)", min_value=0, max_value=80, value=vitals_data.get("respiratory_rate", 16))
        spo2 = st.number_input("SpO2 (%)", min_value=40.0, max_value=100.0, value=vitals_data.get("spo2", 98.0), step=1.0)
        systolic_bp = st.number_input("Systolic BP (mmHg)", min_value=30, max_value=300, value=vitals_data.get("systolic_bp", 122))
        diastolic_bp = st.number_input("Diastolic BP (mmHg)", min_value=20, max_value=200, value=vitals_data.get("diastolic_bp", 78))

    with col3:
        temperature = st.number_input("Temperature (°C)", min_value=28.0, max_value=44.0, value=vitals_data.get("temperature", 37.0), step=0.1)
        pain_score = st.slider("Pain Score (0–10)", min_value=0, max_value=10, value=vitals_data.get("pain_score", 2))
        supplemental_o2 = st.checkbox("Supplemental O2 in use", value=vitals_data.get("supplemental_o2", False))

    st.subheader("2. Clinical Presentation")
    chief_complaint = st.text_area(
        "Chief Complaint",
        value=patient_data.get("chief_complaint", "Patient presents with persistent nausea, jaw tightness, and upper back discomfort."),
        height=70,
    )
    medical_history = st.text_area(
        "Medical History / Comorbidities (leave blank if zero-history / unknown)",
        value=patient_data.get("medical_history", "Hypertension, Hyperlipidemia"),
        height=50,
    )

    resource_choice = st.radio(
        "Estimated Diagnostic/Therapeutic Resources Needed",
        ["None (exam only)", "One (e.g., X-ray or simple script)", "Two or more (labs + imaging + IV)"],
        index=2,
    )
    resources_map = {
        "None (exam only)": 0,
        "One (e.g., X-ray or simple script)": 1,
        "Two or more (labs + imaging + IV)": 2,
    }
    resources_needed = resources_map[resource_choice]

    submitted = st.form_submit_button("🩺 Evaluate & Score Acuity", use_container_width=True)

if submitted:
    st.session_state["intake_start_time"] = time.time()
    # 1. Create Patient & Vitals
    new_patient = Patient(
        name=patient_name,
        age=patient_age,
        sex=patient_sex,
        chief_complaint=chief_complaint,
        medical_history=medical_history,
        status="WAITING",
    )
    new_vitals = VitalSigns(
        patient_id=new_patient.id,
        heart_rate=int(heart_rate),
        respiratory_rate=int(respiratory_rate),
        spo2=float(spo2),
        systolic_bp=int(systolic_bp),
        diastolic_bp=int(diastolic_bp),
        temperature=float(temperature),
        pain_score=int(pain_score),
        consciousness=consciousness,
        supplemental_o2=supplemental_o2,
    )

    insert_patient(conn, new_patient)
    insert_vitals(conn, new_vitals)

    # 2. Analyze Complaint via LLM
    with st.spinner("Analyzing complaint and evaluating clinical risk rules..."):
        analysis = llm.analyze_complaint(chief_complaint, patient_age, patient_sex)
        triage_result = scorer.score(new_patient, new_vitals, analysis, resources_needed)

    update_patient_esi(conn, new_patient.id, triage_result.esi_level)
    insert_triage_result(conn, triage_result)

    st.session_state["current_patient"] = new_patient
    st.session_state["current_vitals"] = new_vitals
    st.session_state["current_triage_result"] = triage_result

if "current_triage_result" in st.session_state and "current_patient" in st.session_state:
    result = st.session_state["current_triage_result"]
    pat = st.session_state["current_patient"]
    vits = st.session_state["current_vitals"]

    st.divider()
    st.subheader("🎯 AI Triage Recommendation")

    esi_colors = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}
    esi_names = {
        1: "ESI 1 — Resuscitation (Immediate)",
        2: "ESI 2 — Emergent (High Risk / Danger Zone)",
        3: "ESI 3 — Urgent (Multiple Resources)",
        4: "ESI 4 — Less Urgent (One Resource)",
        5: "ESI 5 — Non-Urgent (No Resources)",
    }

    badge = esi_colors.get(result.esi_level, "⚪")
    level_name = esi_names.get(result.esi_level, f"ESI {result.esi_level}")

    res_col1, res_col2 = st.columns([1, 2])
    with res_col1:
        st.markdown(f"## {badge} **Level {result.esi_level}**")
        st.caption(level_name)
        st.metric("Confidence", f"{int(result.confidence * 100)}%")
        st.progress(float(result.confidence))

    with res_col2:
        st.markdown(f"### **Justification**: `{result.justification}`")
        if result.red_flags:
            for rf in result.red_flags:
                st.error(f"🚩 **Red Flag Alert**: {rf}")
        else:
            st.success("✅ No acute red flag rules triggered.")

        with st.expander("📊 NEWS2 & Vital Breakdown"):
            st.write(f"**Total NEWS2 Score**: {result.news2_score}")
            st.json(vits.model_dump())

    # Clinician Decision Buttons
    st.divider()
    st.subheader("👩‍⚕️ Clinician Decision Review")
    act_col1, act_col2 = st.columns(2)

    with act_col1:
        if st.button("✅ Accept AI Recommendation", use_container_width=True, type="primary"):
            dwell = round(time.time() - st.session_state.get("intake_start_time", time.time()), 2)
            audit_entry = AuditEntry(
                patient_id=pat.id,
                clinician_id="RN-CurrentShift",
                event_type="ACCEPTED",
                ai_esi=result.esi_level,
                ai_confidence=result.confidence,
                ai_justification=result.justification,
                final_esi=result.esi_level,
                dwell_seconds=dwell,
                vitals_snapshot=vits.model_dump(),
            )
            insert_audit_log(conn, audit_entry)
            st.success(f"Accepted ESI {result.esi_level} for {pat.name}. Recorded in audit log.")

    with act_col2:
        with st.expander("🔄 Override Recommendation", expanded=False):
            override_esi = st.selectbox("Clinician Selected ESI", [1, 2, 3, 4, 5], index=max(0, result.esi_level - 1))
            override_reason = st.selectbox("Override Reason Code", config.OVERRIDE_REASONS)
            override_note = st.text_input("Clinical Rationale Note", value="Patient exhibits atypical severe pain out of proportion.")

            if st.button("Submit Override", use_container_width=True):
                dwell = round(time.time() - st.session_state.get("intake_start_time", time.time()), 2)
                audit_entry = AuditEntry(
                    patient_id=pat.id,
                    clinician_id="RN-CurrentShift",
                    event_type="OVERRIDDEN",
                    ai_esi=result.esi_level,
                    ai_confidence=result.confidence,
                    ai_justification=result.justification,
                    final_esi=override_esi,
                    override_reason_code=override_reason,
                    override_note=override_note,
                    dwell_seconds=dwell,
                    vitals_snapshot=vits.model_dump(),
                )
                insert_audit_log(conn, audit_entry)
                update_patient_esi(conn, pat.id, override_esi)
                st.warning(f"Override recorded: Updated {pat.name} from ESI {result.esi_level} to ESI {override_esi}.")
