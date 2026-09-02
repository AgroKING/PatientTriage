import random
import time
import plotly.express as px
import streamlit as st
import config
from src.database import get_all_patients, init_db
from src.surge_manager import SurgeManager
from src.ui import inject_custom_css, START_COLORS

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("surge_active", False)
st.session_state.setdefault("surge_manager", SurgeManager())
inject_custom_css()

sm: SurgeManager = st.session_state["surge_manager"]

st.title("Surge Mode & Mass-Casualty START Protocol")
st.caption("Rapid mass-casualty triage replacing ESI scoring during acute ED volume spikes or disaster declarations.")

col_btn, col_stat = st.columns([1, 2])
with col_btn:
    if not st.session_state["surge_active"]:
        if st.button("Activate Surge Mode", type="primary", use_container_width=True):
            st.session_state["surge_active"] = True
            sm.activate()
            st.rerun()
    else:
        if st.button("Deactivate Surge Mode", use_container_width=True):
            st.session_state["surge_active"] = False
            sm.deactivate()
            st.rerun()

with col_stat:
    if st.session_state["surge_active"]:
        st.error("**SURGE MODE ACTIVE** — Simple Triage and Rapid Treatment (START) Protocol Engaged")
    else:
        st.info("Surge mode is currently inactive. Standard ESI scoring is in effect across all modules.")


def render_surge_categories(stats: dict, categorized: dict) -> None:
    """Render the 4-column category distribution using proper styled blocks."""
    c_red, c_yellow, c_green, c_blue = st.columns(4)
    order = [
        (c_red,    "RED"),
        (c_yellow, "YELLOW"),
        (c_green,  "GREEN"),
        (c_blue,   "BLUE"),
    ]
    for col, cat_key in order:
        sc = START_COLORS[cat_key]
        # Merge BLACK into BLUE (expectant)
        count = stats.get(cat_key, 0) + (stats.get("BLACK", 0) if cat_key == "BLUE" else 0)
        pids = categorized.get(cat_key, [])
        if cat_key == "BLUE":
            pids = list(dict.fromkeys(pids + categorized.get("BLACK", [])))

        pid_items = "".join(
            f'<div class="surge-pid">{pid[:20]}</div>'
            for pid in pids[:8]  # cap display at 8 per column
        )
        suffix = f'<div class="surge-pid" style="color:#3A404C;">+{len(pids)-8} more</div>' if len(pids) > 8 else ""

        with col:
            st.markdown(
                f'<div class="surge-cat-block cat-{cat_key}">'
                f'<div class="surge-cat-label">{sc["label"]}</div>'
                f'<div class="surge-cat-count cat-{cat_key}">{count}</div>'
                f'{pid_items}{suffix}'
                f'</div>',
                unsafe_allow_html=True,
            )


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

        submitted = st.form_submit_button("Categorize Patient", use_container_width=True)

    if submitted:
        category = sm.start_triage(
            patient_id=patient_id,
            can_walk=can_walk,
            respiratory_rate=rr,
            has_radial_pulse=has_pulse,
            follows_commands=follows_cmd,
            breathing_after_airway=breathing_airway,
        )
        sc = START_COLORS.get(category, START_COLORS["GREEN"])
        st.success(f"Assigned {selected_patient_str} to **{sc['label']}** ({category})")

    # 2. Category Distribution
    st.divider()
    st.subheader("2. Real-Time Surge Protocol Distribution")
    render_surge_categories(sm.get_stats(), sm.get_all_categorized())

    # 3. Simulate 3x Surge — animated
    st.divider()
    st.subheader("3. Disaster Simulation Engine")
    st.caption("Simulate sudden arrival of 30 casualty records under high volume surge conditions.")

    if st.button("Simulate 3x Surge (30 Patients)", use_container_width=True):
        sm.activate()
        progress_bar = st.progress(0)
        cat_placeholder = st.empty()

        TOTAL = 30
        for i in range(1, TOTAL + 1):
            pid = f"SIM-SURGE-{i:03d}"
            rand_roll = random.random()
            if rand_roll < 0.40:
                sm.start_triage(pid, can_walk=True, respiratory_rate=18, has_radial_pulse=True,
                                follows_commands=True, breathing_after_airway=False)
            elif rand_roll < 0.70:
                sm.start_triage(pid, can_walk=False, respiratory_rate=22, has_radial_pulse=True,
                                follows_commands=True, breathing_after_airway=False)
            elif rand_roll < 0.93:
                sm.start_triage(pid, can_walk=False, respiratory_rate=36, has_radial_pulse=False,
                                follows_commands=False, breathing_after_airway=False)
            else:
                sm.start_triage(pid, can_walk=False, respiratory_rate=0, has_radial_pulse=False,
                                follows_commands=False, breathing_after_airway=False)

            progress_bar.progress(i / TOTAL)

            # Update category display every 5 patients
            if i % 5 == 0 or i == TOTAL:
                stats_live = sm.get_stats()
                cat_live = sm.get_all_categorized()
                with cat_placeholder.container():
                    render_surge_categories(stats_live, cat_live)

            time.sleep(0.04)

        progress_bar.empty()
        st.toast(f"Surge simulation complete — {TOTAL} patients categorized", icon=None)
        st.rerun()

    # Chart
    counts = sm.get_stats()
    df_chart = []
    for k, v in counts.items():
        cat_name = "BLUE" if k in ("BLACK", "BLUE") else k
        df_chart.append({"Category": cat_name, "Count": v})

    color_map = {k: START_COLORS[k]["border"] for k in START_COLORS}
    fig = px.bar(
        df_chart,
        x="Category",
        y="Count",
        color="Category",
        color_discrete_map=color_map,
        title="START Category Allocation",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E8E9EB",
    )
    st.plotly_chart(fig, use_container_width=True)

