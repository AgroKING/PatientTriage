import pandas as pd
import streamlit as st
import config
from src.database import get_audit_trail, get_patient, init_db
from src.ui import inject_custom_css, AUDIT_EVENT_COLORS, ESI_NAMES, esi_badge_html

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)
inject_custom_css()

st.title("Clinical Audit Trail & Override Log")
st.caption("Immutable append-only record of AI triage predictions, clinician validations, overrides, and latency metrics.")

raw_audit = get_audit_trail(conn)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    search_name = st.text_input("Filter by Patient Name or ID", "")
with col_f2:
    event_filter = st.multiselect(
        "Event Type Filter",
        ["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"],
        default=["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"],
    )

# ── Filter & build rows ───────────────────────────────────────────────────────
filtered_rows = []
filtered_entries = []
for entry in raw_audit:
    p_info = get_patient(conn, entry["patient_id"]) or {}
    p_name = p_info.get("name", "Unknown")

    if search_name:
        s = search_name.lower()
        if s not in p_name.lower() and s not in entry["patient_id"].lower():
            continue

    if entry["event_type"] not in event_filter:
        continue

    filtered_entries.append((entry, p_name))
    filtered_rows.append({
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
    })

# Reverse-chronological — most recent first
filtered_entries = list(reversed(filtered_entries))

if not filtered_entries:
    st.info("No audit logs found matching the selected filters.")
else:
    st.divider()

    # Pagination cap
    LIMIT = 50
    show_all = st.session_state.get("audit_show_all", False)
    total = len(filtered_entries)
    display_entries = filtered_entries if show_all else filtered_entries[:LIMIT]

    st.caption(f"Showing {len(display_entries)} of {total} entries, newest first.")

    # ── Timeline ──────────────────────────────────────────────────────────────
    for entry, p_name in display_entries:
        evt = entry.get("event_type", "SCORED")
        ec = AUDIT_EVENT_COLORS.get(evt, AUDIT_EVENT_COLORS["SCORED"])
        ai_esi = entry.get("ai_esi") or "—"
        final_esi = entry.get("final_esi") or "—"
        conf_pct = int((entry.get("ai_confidence") or 0) * 100)
        dwell = entry.get("dwell_seconds")
        dwell_str = f"{dwell}s" if dwell else "—"
        ts = entry.get("timestamp", "")[:19].replace("T", " ")  # trim microseconds

        # ESI change arrow
        if ai_esi != "—" and final_esi != "—" and int(ai_esi) != int(final_esi):
            esi_delta = f"AI {ai_esi} → Clinician {final_esi}"
        else:
            esi_delta = f"ESI {final_esi}"

        # Badge inline HTML (no st.markdown for the header, keep it in expander label)
        badge_style = (
            f"background:{ec['bg']};color:{ec['text']};"
            f"border-radius:3px;padding:1px 6px;font-size:0.72rem;"
            f"font-family:'IBM Plex Mono',monospace;font-weight:600;"
            f"letter-spacing:0.04em;"
        )
        expander_label = f"[{ts}]  {evt}  —  {p_name}  ({esi_delta})"

        with st.expander(expander_label, expanded=False):
            # Left-border via container + inline div wrapper
            st.markdown(
                f'<div class="timeline-entry evt-{evt}" style="padding:4px 0 4px 10px;">',
                unsafe_allow_html=True,
            )

            detail_col1, detail_col2 = st.columns([3, 2])
            with detail_col1:
                st.markdown(f"**Patient:** {p_name} &nbsp; `{entry['patient_id']}`")
                st.markdown(f"**Clinician:** {entry.get('clinician_id', '—')}")
                justification = entry.get("ai_justification") or "—"
                st.markdown(f"**AI Justification:** {justification}")

                override_reason = entry.get("override_reason_code")
                override_note = entry.get("override_note")
                if override_reason:
                    st.markdown(f"**Override Reason:** `{override_reason}`")
                if override_note:
                    st.markdown(f"**Override Note:** {override_note}")

            with detail_col2:
                if ai_esi != "—":
                    st.markdown(f"**AI Score:** {esi_badge_html(int(ai_esi))} &nbsp; {conf_pct}% confidence", unsafe_allow_html=True)
                if final_esi != "—":
                    st.markdown(f"**Final ESI:** {esi_badge_html(int(final_esi))}", unsafe_allow_html=True)
                st.markdown(f"**Dwell Time:** `{dwell_str}`")

            st.markdown('</div>', unsafe_allow_html=True)

    if not show_all and total > LIMIT:
        st.write("")
        if st.button(f"Show all {total} entries", use_container_width=False):
            st.session_state["audit_show_all"] = True
            st.rerun()
    elif show_all and total > LIMIT:
        if st.button("Show recent 50 only", use_container_width=False):
            st.session_state["audit_show_all"] = False
            st.rerun()

    st.divider()

    # ── CSV Export ────────────────────────────────────────────────────────────
    if filtered_rows:
        df_audit = pd.DataFrame(list(reversed(filtered_rows)))  # keep CSV in reverse-chron too
        csv_data = df_audit.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Audit Trail CSV",
            data=csv_data,
            file_name="patient_triage_audit_log.csv",
            mime="text/csv",
        )
