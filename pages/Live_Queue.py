import time
import pandas as pd
import streamlit as st
import config
from src.database import init_db
from src.queue_manager import check_deterioration_alerts, get_ranked_queue
from src.ui import inject_custom_css, ESI_COLORS, ESI_NAMES, esi_badge_html, format_wait_time

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("queue_last_refresh", time.time())

inject_custom_css()

st.title("Live ED Priority Queue")
st.caption("Acuity ranking by ESI level and elapsed wait time. Deterioration alerts fire when safe wait limits are exceeded.")


def render_queue():
    ranked_patients = get_ranked_queue(conn)
    alerts = check_deterioration_alerts(conn)

    # ── Last-updated indicator ─────────────────────────────────────────────────
    now = time.time()
    elapsed = int(now - st.session_state.get("queue_last_refresh", now))
    st.session_state["queue_last_refresh"] = now
    elapsed_str = f"{elapsed}s ago" if elapsed < 60 else f"{elapsed // 60}m ago"
    st.markdown(
        f'<div class="live-indicator">'
        f'<span class="live-dot"></span>'
        f'Refreshing every 5s &nbsp;·&nbsp; last updated {elapsed_str}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.write("")  # small spacer

    # ── 1. Deterioration Alerts ────────────────────────────────────────────────
    if alerts:
        st.subheader(f"Deterioration Alerts ({len(alerts)})")
        for a in alerts:
            esi = a["esi_level"]
            c = ESI_COLORS.get(esi, {"border": "#5B6472", "bg": "rgba(91,100,114,0.18)"})
            st.markdown(
                f'<div class="det-alert det-alert-esi-{esi}">'
                f'<strong>{a["name"]}</strong> {esi_badge_html(esi)} '
                f'waiting <span class="eq-mono"><strong>{format_wait_time(a["wait_minutes"])}</strong></span> '
                f'— exceeds {a["threshold_minutes"]}m limit '
                f'(<span class="eq-mono">+{a["overdue_minutes"]}m overdue</span>)'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.success("All waiting patients are within clinical wait time thresholds.")

    st.divider()

    # ── 2. Queue summary metrics ───────────────────────────────────────────────
    st.subheader(f"Waiting Room — {len(ranked_patients)} patients")

    esi_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    esi_waits: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for p in ranked_patients:
        e = p.get("esi_level", 3)
        if e in esi_counts:
            esi_counts[e] += 1
            esi_waits[e].append(p.get("wait_minutes", 0))

    mcol1, mcol2, mcol3, mcol4, mcol5, mcol6 = st.columns(6)
    mcol1.metric("Total", len(ranked_patients))
    mcol2.metric("ESI 1", esi_counts[1])
    mcol3.metric("ESI 2", esi_counts[2])
    mcol4.metric("ESI 3", esi_counts[3])
    mcol5.metric("ESI 4", esi_counts[4])
    mcol6.metric("ESI 5", esi_counts[5])

    # Avg wait chips
    chips_html = ""
    for lvl in range(1, 6):
        avg = sum(esi_waits[lvl]) / len(esi_waits[lvl]) if esi_waits[lvl] else 0
        c = ESI_COLORS[lvl]
        chips_html += (
            f'<div class="wait-chip" style="border-top:2px solid {c["border"]};">'
            f'<span class="wait-chip-label">ESI {lvl} avg</span>'
            f'<span class="wait-chip-value">{format_wait_time(avg)}</span>'
            f'</div>'
        )
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;margin-top:12px;">' + chips_html + '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 3. ESI-grouped card list ───────────────────────────────────────────────
    if not ranked_patients:
        st.info("No patients currently in the waiting queue.")
        return

    # Group by ESI level, preserve rank ordering within each group
    by_esi: dict[int, list] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for rank, p in enumerate(ranked_patients, 1):
        esi = p.get("esi_level", 3)
        if esi in by_esi:
            by_esi[esi].append((rank, p))

    for lvl in range(1, 6):
        group = by_esi[lvl]
        if not group:
            continue

        c = ESI_COLORS[lvl]
        section_label = ESI_NAMES.get(lvl, f"ESI {lvl}")
        st.markdown(
            f'<div class="queue-section-header" style="color:{c["text"]}">'
            f'{section_label} &nbsp;·&nbsp; {len(group)} patient{"s" if len(group) != 1 else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        for rank, p in group:
            name = p.get("name", "Unknown")
            esi = p.get("esi_level", 3)
            wait_str = format_wait_time(p.get("wait_minutes", 0))
            score = round(p.get("priority_score", 0), 1)
            status = p.get("status", "WAITING")
            comp = p.get("chief_complaint", "")
            if len(comp) > 65:
                comp = comp[:62] + "..."

            st.markdown(
                f'<div class="patient-card esi-{esi}">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'  <div>'
                f'    <div class="patient-card-name">#{rank} &nbsp; {name}</div>'
                f'    <div class="patient-card-meta">'
                f'      {esi_badge_html(esi)}'
                f'      &nbsp;&nbsp;'
                f'      <span class="patient-card-wait">{wait_str}</span>'
                f'      &nbsp;·&nbsp; score <span class="eq-mono">{score}</span>'
                f'      &nbsp;·&nbsp; {status}'
                f'    </div>'
                f'    <div class="patient-card-complaint">{comp}</div>'
                f'  </div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.write("")  # section gap


if hasattr(st, "fragment"):
    @st.fragment(run_every=5)
    def auto_refresh_queue():
        render_queue()
    auto_refresh_queue()
else:
    render_queue()
