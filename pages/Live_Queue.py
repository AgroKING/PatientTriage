import pandas as pd
import streamlit as st
import config
from src.database import init_db
from src.queue_manager import check_deterioration_alerts, get_ranked_queue
from src.ui import inject_custom_css

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)

inject_custom_css()

st.title("Live ED Priority Queue & Deterioration Monitor")
st.caption("Auto-refreshing dynamic acuity ranking based on ESI level and waiting room elapsed time.")

def render_queue():
    ranked_patients = get_ranked_queue(conn)
    alerts = check_deterioration_alerts(conn)

    # 1. Deterioration Alerts
    if alerts:
        st.subheader("Deterioration Alerts (Safe Wait Limit Exceeded)")
        color_map = {
            1: {"border": "#DC2626", "bg": "rgba(220, 38, 38, 0.18)"},
            2: {"border": "#EA580C", "bg": "rgba(234, 88, 12, 0.18)"},
            3: {"border": "#CA8A04", "bg": "rgba(202, 138, 4, 0.18)"},
            4: {"border": "#16A34A", "bg": "rgba(22, 163, 74, 0.18)"},
            5: {"border": "#2563EB", "bg": "rgba(37, 99, 235, 0.18)"},
        }
        for a in alerts:
            esi = a["esi_level"]
            info = color_map.get(esi, {"border": "#5B6472", "bg": "rgba(91, 100, 114, 0.18)"})
            alert_html = (
                f'<div style="padding:12px 16px; margin-bottom:8px; border-radius:8px; '
                f'background:{info["bg"]}; border:1px solid #5B6472; border-left:6px solid {info["border"]}; '
                f'color:#E8E9EB; font-family:\'Inter\', sans-serif; font-size:0.9rem;">'
                f'<strong>{a["name"]}</strong> (ESI {esi}) waiting <span class="eq-mono"><strong>{a["wait_minutes"]}m</strong></span> '
                f'— exceeds {a["threshold_minutes"]}m safe limit (<span class="eq-mono">+{a["overdue_minutes"]}m overdue</span>)'
                f'</div>'
            )
            st.markdown(alert_html, unsafe_allow_html=True)
    else:
        st.success("All waiting patients are within clinical wait time thresholds.")

    st.divider()

    # 2. Ranked Queue Table
    st.subheader(f"Waiting Room Queue ({len(ranked_patients)} Patients)")

    if not ranked_patients:
        st.info("No patients currently in the waiting queue.")
    else:
        def format_wait(mins: float) -> str:
            if mins < 60:
                return f"{int(mins)}m"
            hours = int(mins // 60)
            rem = int(mins % 60)
            return f"{hours}h {rem}m"

        rows_html = []
        for rank, p in enumerate(ranked_patients, 1):
            comp = p.get("chief_complaint", "")
            if len(comp) > 50:
                comp = comp[:47] + "..."

            esi = p.get("esi_level", 3)
            wait_str = format_wait(p.get("wait_minutes", 0))
            score = round(p.get("priority_score", 0), 1)
            status = p.get("status", "WAITING")
            name = p.get("name", "Unknown")

            rows_html.append(
                f'<tr class="eq-esi-{esi}">'
                f'<td class="eq-mono">{rank}</td>'
                f'<td>{name}</td>'
                f'<td class="eq-esi-label">ESI {esi}</td>'
                f'<td>{comp}</td>'
                f'<td class="eq-mono">{wait_str}</td>'
                f'<td class="eq-mono">{score}</td>'
                f'<td>{status}</td>'
                f'</tr>'
            )

        table_html = (
            '<table class="eq-table"><thead><tr>'
            '<th>Rank</th><th>Patient</th><th>ESI</th>'
            '<th>Chief Complaint</th><th>Wait</th>'
            '<th>Priority</th><th>Status</th>'
            '</tr></thead><tbody>'
            + "".join(rows_html)
            + '</tbody></table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

    # 3. Summary Metrics
    st.divider()
    st.subheader("Queue Analytics & Acuity Distribution")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Waiting", len(ranked_patients))

    esi_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    esi_waits = {1: [], 2: [], 3: [], 4: [], 5: []}

    for p in ranked_patients:
        e = p.get("esi_level", 3)
        if e in esi_counts:
            esi_counts[e] += 1
            esi_waits[e].append(p.get("wait_minutes", 0))

    col2.metric("ESI 1", esi_counts[1])
    col3.metric("ESI 2", esi_counts[2])
    col4.metric("ESI 3", esi_counts[3])
    col5.metric("ESI 4", esi_counts[4])
    col6.metric("ESI 5", esi_counts[5])

    st.caption("Average Wait Times by Level:")
    avg_waits = {}
    for lvl in range(1, 6):
        avg = sum(esi_waits[lvl]) / len(esi_waits[lvl]) if esi_waits[lvl] else 0
        avg_waits[f"ESI {lvl}"] = f"{round(avg, 1)} min"
    st.write(avg_waits)

if hasattr(st, "fragment"):
    @st.fragment(run_every=5)
    def auto_refresh_queue():
        render_queue()
    auto_refresh_queue()
else:
    render_queue()
