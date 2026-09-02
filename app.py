import streamlit as st
import config
from src.database import get_all_patients, get_all_waiting_patients, init_db
from src.queue_manager import check_deterioration_alerts
from src.data_loader import seed_demo_patients
from src.ui import inject_custom_css, ICON_INTAKE, ICON_QUEUE, ICON_AUDIT, ICON_SURGE

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="T",
    layout="wide",
)

conn = init_db(config.DB_PATH)
seed_demo_patients(conn)

st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("surge_active", False)

inject_custom_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("PatientTriage.ai")
st.sidebar.caption("AI-Assisted ED Triage Decision Support")
st.sidebar.divider()
st.sidebar.warning("DEMO — Public Dataset — Not for Clinical Use")

all_patients = get_all_patients(conn)
waiting_patients = get_all_waiting_patients(conn)
alerts = check_deterioration_alerts(conn)

esi_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
for p in waiting_patients:
    esi = p.get("current_esi")
    if esi in esi_counts:
        esi_counts[esi] += 1

st.sidebar.subheader("Emergency Dept Status")
col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("Total Waiting", len(waiting_patients))
col_s2.metric("Active Alerts", len(alerts), delta_color="inverse")

esi_names_sidebar = {1: "ESI 1 Resus", 2: "ESI 2 Emrg", 3: "ESI 3 Urgn", 4: "ESI 4 Less", 5: "ESI 5 Non"}
esi_strip_items = []
for lvl in range(1, 6):
    cnt = esi_counts[lvl]
    cls = f"esi-{lvl}" if cnt > 0 else f"esi-{lvl} esi-empty"
    esi_strip_items.append(
        f'<div class="esi-strip-item {cls}">'
        f'<span class="esi-count">{cnt}</span>'
        f'<span>{esi_names_sidebar[lvl]}</span>'
        f'</div>'
    )
alert_class = "sidebar-alert-active" if len(alerts) > 0 else ""
st.sidebar.markdown(
    f'<div class="esi-strip {alert_class}">' + "".join(esi_strip_items) + '</div>',
    unsafe_allow_html=True,
)

# ── Main ──────────────────────────────────────────────────────────────────────

st.title("PatientTriage.ai")
st.caption("A triage nurse gets about 90 seconds per patient. This is the math behind that call.")

st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**ESI 1–5, live**")
    st.caption("Age-adjusted risk, NEWS2, red flags, chief complaint — scored together, not eyeballed.")
with col2:
    st.markdown("**Errs toward caution**")
    st.caption("Ambiguous cases get pushed up, not down. A silent MI doesn't get to hide in ESI 4.")
with col3:
    st.markdown("**Queue keeps moving**")
    st.caption("Re-ranks on wait time and acuity, not just at intake. Deterioration triggers an alert.")
with col4:
    st.markdown("**Nothing gets erased**")
    st.caption("Every score, override, and reason for it — logged, append-only, exportable.")

st.divider()

# ── Navigation Cards ──────────────────────────────────────────────────────────
NAV_PAGES = [
    {
        "icon": ICON_INTAKE,
        "title": "Patient Intake",
        "desc": "Enter vitals and chief complaint manually or load a case from the dataset. Runs ESI scoring with visible reasoning steps.",
        "page": "pages/Patient_Intake.py",
    },
    {
        "icon": ICON_QUEUE,
        "title": "Live Queue",
        "desc": "Waiting room ranked by acuity and elapsed time. Auto-refreshes every 5 seconds. Flags patients past their safe wait limit.",
        "page": "pages/Live_Queue.py",
    },
    {
        "icon": ICON_AUDIT,
        "title": "Audit Log",
        "desc": "Append-only record of every AI score, clinician acceptance, and override — with justification and dwell time. CSV export.",
        "page": "pages/Audit_Log.py",
    },
    {
        "icon": ICON_SURGE,
        "title": "Surge Mode",
        "desc": "Activates START mass-casualty protocol. Replaces ESI scoring with RED / YELLOW / GREEN / BLUE field triage categories.",
        "page": "pages/Surge_Mode.py",
    },
]

nav_cols = st.columns(4)
for col, page in zip(nav_cols, NAV_PAGES):
    with col:
        st.markdown(
            f'<div class="nav-card">'
            f'<span class="nav-card-icon">{page["icon"]}</span>'
            f'<div class="nav-card-title">{page["title"]}</div>'
            f'<div class="nav-card-desc">{page["desc"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(f"Open {page['title']}", key=f"nav_{page['title']}", use_container_width=True):
            st.switch_page(page["page"])

st.divider()

# ── Bottom metrics ────────────────────────────────────────────────────────────
surge_status = "Active" if st.session_state.get("surge_active") else "Normal"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Registered", len(all_patients))
m2.metric("Waiting", len(waiting_patients))
m3.metric("Alerts", len(alerts))
m4.metric("Surge Protocol", surge_status)