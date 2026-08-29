import pandas as pd
import streamlit as st
import config
from src.database import get_audit_trail, get_patient, init_db

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)

st.title("📝 Clinical Audit Trail & Override Log")
st.caption("Immutable append-only record of AI triage predictions, clinician validations, overrides, and latency metrics.")

raw_audit = get_audit_trail(conn)

# Filters
col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    search_name = st.text_input("Filter by Patient Name or ID", "")
with col_f2:
    event_filter = st.multiselect(
        "Event Type Filter",
        ["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"],
        default=["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"],
    )

filtered_rows = []
for entry in raw_audit:
    p_info = get_patient(conn, entry["patient_id"]) or {}
    p_name = p_info.get("name", "Unknown")

    if search_name:
        s = search_name.lower()
        if s not in p_name.lower() and s not in entry["patient_id"].lower():
            continue

    if entry["event_type"] not in event_filter:
        continue

    row = {
        "Timestamp": entry["timestamp"],
        "Patient ID": entry["patient_id"],
        "Patient Name": p_name,
        "Clinician ID": entry["clinician_id"],
        "Event Type": entry["event_type"],
        "AI ESI": entry["ai_esi"],
        "AI Confidence": f"{int((entry.get('ai_confidence') or 0) * 100)}%",
        "AI Justification": entry.get("ai_justification", ""),
        "Final ESI": entry["final_esi"],
        "Override Reason": entry.get("override_reason_code") or "—",
        "Override Note": entry.get("override_note") or "—",
        "Dwell Time (s)": entry.get("dwell_seconds") or "—",
    }
    filtered_rows.append(row)

if filtered_rows:
    df_audit = pd.DataFrame(filtered_rows)
    st.dataframe(df_audit, use_container_width=True, hide_index=True)

    csv_data = df_audit.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Audit Trail CSV",
        data=csv_data,
        file_name="patient_triage_audit_log.csv",
        mime="text/csv",
    )
else:
    st.info("No audit logs found matching the selected filters.")
