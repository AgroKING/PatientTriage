import pandas as pd
import streamlit as st
import config
from src.database import init_db
from src.queue_manager import check_deterioration_alerts, get_ranked_queue

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)

st.title("📊 Live ED Priority Queue & Deterioration Monitor")
st.caption("Auto-refreshing dynamic acuity ranking based on ESI level and waiting room elapsed time.")

def render_queue():
    ranked_patients = get_ranked_queue(conn)
    alerts = check_deterioration_alerts(conn)

    # 1. Deterioration Alerts
    if alerts:
        st.subheader("🚨 Deterioration Alerts (Safe Wait Limit Exceeded)")
        for a in alerts:
            alert_msg = f"⚠️ **{a['name']}** (ESI {a['esi_level']}) waiting **{a['wait_minutes']}m** — exceeds {a['threshold_minutes']}m safe limit (+{a['overdue_minutes']}m overdue)"
            if a["esi_level"] <= 2:
                st.error(alert_msg)
            else:
                st.warning(alert_msg)
    else:
        st.success("✅ All waiting patients are within clinical wait time thresholds.")

    st.divider()

    # 2. Ranked Queue Table
    st.subheader(f"Waiting Room Queue ({len(ranked_patients)} Patients)")

    if not ranked_patients:
        st.info("No patients currently in the waiting queue.")
    else:
        esi_badges = {1: "🔴 ESI 1", 2: "🟠 ESI 2", 3: "🟡 ESI 3", 4: "🟢 ESI 4", 5: "🔵 ESI 5"}

        def format_wait(mins: float) -> str:
            if mins < 60:
                return f"{int(mins)}m"
            hours = int(mins // 60)
            rem = int(mins % 60)
            return f"{hours}h {rem}m"

        table_data = []
        for rank, p in enumerate(ranked_patients, 1):
            comp = p.get("chief_complaint", "")
            if len(comp) > 50:
                comp = comp[:47] + "..."

            esi = p.get("esi_level", 3)
            badge = esi_badges.get(esi, f"ESI {esi}")

            table_data.append({
                "Rank (#)": rank,
                "Patient Name": p.get("name", "Unknown"),
                "ESI Level": badge,
                "Chief Complaint": comp,
                "Wait Time": format_wait(p.get("wait_minutes", 0)),
                "Priority Score": round(p.get("priority_score", 0), 1),
                "Status": p.get("status", "WAITING"),
            })

        df_display = pd.DataFrame(table_data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    # 3. Summary Metrics
    st.divider()
    st.subheader("📈 Queue Analytics & Acuity Distribution")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Waiting", len(ranked_patients))

    esi_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    esi_waits = {1: [], 2: [], 3: [], 4: [], 5: []}

    for p in ranked_patients:
        e = p.get("esi_level", 3)
        if e in esi_counts:
            esi_counts[e] += 1
            esi_waits[e].append(p.get("wait_minutes", 0))

    col2.metric("🔴 ESI 1", esi_counts[1])
    col3.metric("🟠 ESI 2", esi_counts[2])
    col4.metric("🟡 ESI 3", esi_counts[3])
    col5.metric("🟢 ESI 4", esi_counts[4])
    col6.metric("🔵 ESI 5", esi_counts[5])

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
