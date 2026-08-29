import random
import plotly.express as px
import streamlit as st
import config
from src.database import get_all_patients, init_db
from src.surge_manager import SurgeManager

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("surge_active", False)
st.session_state.setdefault("surge_manager", SurgeManager())

sm: SurgeManager = st.session_state["surge_manager"]

st.title("🚨 Surge Mode & Mass-Casualty START Protocol")
st.caption("Rapid mass-casualty triage replacing ESI scoring during acute ED volume spikes or disaster declarations.")

col_btn, col_stat = st.columns([1, 2])
with col_btn:
    if not st.session_state["surge_active"]:
        if st.button("🚨 Activate Surge Mode", type="primary", use_container_width=True):
            st.session_state["surge_active"] = True
            sm.activate()
            st.rerun()
    else:
        if st.button("🟢 Deactivate Surge Mode", use_container_width=True):
            st.session_state["surge_active"] = False
            sm.deactivate()
            st.rerun()

with col_stat:
    if st.session_state["surge_active"]:
        st.error("🚨 **SURGE MODE ACTIVE** — Simple Triage and Rapid Treatment (START) Protocol Engaged")
    else:
        st.info("ℹ️ Surge mode is currently inactive. Standard ESI scoring is in effect across all modules.")

if st.session_state["surge_active"]:
    st.divider()
    st.subheader("1. START Field Triage Assessment")

    all_p = get_all_patients(conn)
    patient_names = [f"{p['name']} ({p['id']})" for p in all_p] if all_p else ["Jane Doe (DEMO-001)"]

    with st.form("start_triage_form"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            selected_patient_str = st.selectbox("Select Patient or Enter ID", patient_names)
            patient_id = selected_patient_str.split("(")[-1].replace(")", "").strip()
            can_walk = st.radio("Can the patient walk?", ["Yes", "No"], horizontal=True) == "Yes"

        with col_p2:
            if not can_walk:
                rr = st.number_input("Respiratory Rate (breaths/min)", min_value=0, max_value=80, value=20)
                if rr == 0:
                    breathing_airway = st.checkbox("Breathing restored after airway opening?", value=False)
                    has_pulse = False
                    follows_cmd = False
                else:
                    breathing_airway = False
                    has_pulse = st.checkbox("Radial pulse present?", value=True)
                    follows_cmd = st.checkbox("Follows simple verbal commands?", value=True)
            else:
                rr = 18
                breathing_airway = False
                has_pulse = True
                follows_cmd = True

        submitted = st.form_submit_button("🏷️ Categorize Patient", use_container_width=True)

    if submitted:
        category = sm.start_triage(
            patient_id=patient_id,
            can_walk=can_walk,
            respiratory_rate=rr,
            has_radial_pulse=has_pulse,
            follows_commands=follows_cmd,
            breathing_after_airway=breathing_airway,
        )
        cat_emojis = {"RED": "🔴 IMMEDIATE", "YELLOW": "🟡 DELAYED", "GREEN": "🟢 MINOR", "BLACK": "⚫ EXPECTANT"}
        st.success(f"Assigned {selected_patient_str} to **{cat_emojis.get(category, category)}**")

    # 2. Category Distribution Columns
    st.divider()
    st.subheader("2. Real-Time Surge Protocol Distribution")

    stats = sm.get_stats()
    categorized = sm.get_all_categorized()

    c_red, c_yellow, c_green, c_black = st.columns(4)

    with c_red:
        st.error(f"🔴 IMMEDIATE\n### {stats.get('RED', 0)}")
        for pid in categorized.get("RED", []):
            st.caption(f"• {pid}")

    with c_yellow:
        st.warning(f"🟡 DELAYED\n### {stats.get('YELLOW', 0)}")
        for pid in categorized.get("YELLOW", []):
            st.caption(f"• {pid}")

    with c_green:
        st.success(f"🟢 MINOR\n### {stats.get('GREEN', 0)}")
        for pid in categorized.get("GREEN", []):
            st.caption(f"• {pid}")

    with c_black:
        st.info(f"⚫ EXPECTANT\n### {stats.get('BLACK', 0)}")
        for pid in categorized.get("BLACK", []):
            st.caption(f"• {pid}")

    # 3. Simulate 3x Surge
    st.divider()
    st.subheader("3. Disaster Simulation Engine")
    st.caption("Simulate sudden arrival of 30 casualty records under high volume surge conditions.")

    if st.button("⚡ Simulate 3× Surge (30 Patients)", use_container_width=True):
        sm.activate()
        for i in range(1, 31):
            pid = f"SIM-SURGE-{i:03d}"
            # Random distribution of conditions
            rand_roll = random.random()
            if rand_roll < 0.40:
                # Minor walking wounded
                sm.start_triage(pid, can_walk=True, respiratory_rate=18, has_radial_pulse=True, follows_commands=True, breathing_after_airway=False)
            elif rand_roll < 0.70:
                # Delayed
                sm.start_triage(pid, can_walk=False, respiratory_rate=22, has_radial_pulse=True, follows_commands=True, breathing_after_airway=False)
            elif rand_roll < 0.93:
                # Immediate
                sm.start_triage(pid, can_walk=False, respiratory_rate=36, has_radial_pulse=False, follows_commands=False, breathing_after_airway=False)
            else:
                # Expectant
                sm.start_triage(pid, can_walk=False, respiratory_rate=0, has_radial_pulse=False, follows_commands=False, breathing_after_airway=False)

        st.rerun()

    # Chart
    counts = sm.get_stats()
    df_chart = [{"Category": k, "Count": v} for k, v in counts.items()]
    color_map = {"RED": "#EF4444", "YELLOW": "#F59E0B", "GREEN": "#10B981", "BLACK": "#1F2937"}
    fig = px.bar(
        df_chart,
        x="Category",
        y="Count",
        color="Category",
        color_discrete_map=color_map,
        title="START Category Allocation",
    )
    st.plotly_chart(fig, use_container_width=True)
