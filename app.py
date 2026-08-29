import streamlit as st
import config
from src.database import get_all_patients, get_all_waiting_patients, init_db
from src.queue_manager import check_deterioration_alerts
from src.data_loader import seed_demo_patients

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="🏥",
    layout="wide",
)

conn = init_db(config.DB_PATH)
seed_demo_patients(conn)

st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("surge_active", False)

# Inject custom premium styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply Outfit font to all elements */
    html, body, [class*="css"], .stMarkdown, .stText, p, div, span, label, h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Style block alerts to look premium */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Premium medical card containers using container boxes */
    div[data-testid="stMetricContainer"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 15px 20px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stMetricContainer"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
    }
    
    /* Pulsing animation for active alarms */
    @keyframes pulse-red {
        0% { border-color: rgba(239, 68, 68, 0.4); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.2); }
        70% { border-color: rgba(239, 68, 68, 0.8); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { border-color: rgba(239, 68, 68, 0.4); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    
    /* Apply red pulsing warning borders to active alerts in sidebar/main */
    .pulse-alarm {
        animation: pulse-red 2s infinite !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.title("🏥 PatientTriage.ai")
st.sidebar.caption("AI-Assisted ED Triage Decision Support")
st.sidebar.divider()
st.sidebar.warning("DEMO — Public Dataset — Not for Clinical Use")

# Sidebar Live Metrics
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

st.sidebar.caption(
    f"🔴 ESI 1: **{esi_counts[1]}** | 🟠 ESI 2: **{esi_counts[2]}** | "
    f"🟡 ESI 3: **{esi_counts[3]}** | 🟢 ESI 4: **{esi_counts[4]}** | 🔵 ESI 5: **{esi_counts[5]}**"
)

# Main Welcome Page
st.title("🏥 PatientTriage.ai")
st.subheader("Emergency Department Intelligent Decision Support & Dynamic Queue Management")

st.markdown(
    """
Welcome to **PatientTriage.ai**, an emergency department decision-support system designed to assist
triage nurses during rapid patient intake, acute risk stratification, and dynamic waiting-room management.

### Key Capabilities
- **⚡ Rapid Triage Scoring (ESI 1–5)**: Combines age-adjusted clinical danger zones, NEWS2 score, red-flag heuristics, and LLM chief complaint analysis.
- **🛡️ Asymmetric Safety Escalation**: Calibrated to over-triage ambiguous or high-risk cases (e.g. female atypical cardiac symptoms, silent MI in diabetics, pediatric compensated shock).
- **⏱️ Dynamic Acuity Queue**: Re-ranks patients in real time based on both acuity and wait time, with automated deterioration alerts.
- **📝 Complete Audit Trail**: Append-only logging of all AI recommendations, clinician reviews, override rationale, and dwell times.
- **🚨 START Surge Protocol**: Instant switch to Simple Triage and Rapid Treatment (START) during mass casualty or emergency surges.

---
### Navigation
Use the left sidebar to navigate between operational modules:
1. **📋 Patient Intake**: Perform manual intake or load test cases from dataset.
2. **📊 Live Queue**: Real-time waiting room priority queue with deterioration monitoring.
3. **📝 Audit Log**: Comprehensive inspection and CSV export of all triage decisions and overrides.
4. **🚨 Surge Mode**: Mass casualty START protocol with simulated high-volume load testing.
"""
)

# Quick status display
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.info(f"**Total Registered Patients**\n# {len(all_patients)}")
c2.warning(f"**Currently Waiting**\n# {len(waiting_patients)}")
c3.error(f"**Deterioration Alerts**\n# {len(alerts)}")
surge_status = "ACTIVE 🚨" if st.session_state.get("surge_active") else "NORMAL 🟢"
c4.success(f"**Surge Protocol**\n{surge_status}")
