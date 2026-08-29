import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base typography: Inter everywhere ── */
html, body, p, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText {
    font-family: 'Inter', 'IBM Plex Sans', sans-serif;
}

/* ── Metric containers: flat graphite-800, no hover-lift ── */
div[data-testid="stMetricContainer"] {
    background: #1C2027 !important;
    border: 1px solid #5B6472 !important;
    border-radius: 8px !important;
    padding: 15px 20px !important;
}

/* ── Alerts: flat, no blur, no glow ── */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    box-shadow: none !important;
}

/* ── Monospace utility for vitals / data numerals ── */
.mono-data, .eq-mono {
    font-family: 'IBM Plex Mono', monospace !important;
    font-variant-numeric: tabular-nums !important;
}

/* ── Sidebar ESI status strip ── */
.esi-strip {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 8px 0;
}
.esi-strip-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    font-size: 0.85rem;
    color: #E8E9EB;
    border-left: 3px solid transparent;
    font-family: 'Inter', sans-serif;
}
.esi-strip-item .esi-count {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    min-width: 1.5ch;
    text-align: right;
}
.esi-strip-item.esi-1 { border-left-color: #DC2626; }
.esi-strip-item.esi-2 { border-left-color: #EA580C; }
.esi-strip-item.esi-3 { border-left-color: #CA8A04; }
.esi-strip-item.esi-4 { border-left-color: #16A34A; }
.esi-strip-item.esi-5 { border-left-color: #2563EB; }
.esi-strip-item.esi-empty { border-left-color: #5B6472; opacity: 0.5; }

/* ── Live Queue ops-board table ── */
.eq-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #E8E9EB;
}
.eq-table thead th {
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #5B6472;
    border-bottom: 2px solid #5B6472;
    background: #14171C;
}
.eq-table tbody tr {
    border-bottom: 1px solid rgba(91,100,114,0.3);
}
.eq-table tbody td {
    padding: 10px 12px;
    vertical-align: middle;
}
.eq-table tbody tr td:first-child {
    border-left: 4px solid transparent;
    padding-left: 10px;
}
.eq-table tbody tr.eq-esi-1 td:first-child { border-left-color: #DC2626; }
.eq-table tbody tr.eq-esi-2 td:first-child { border-left-color: #EA580C; }
.eq-table tbody tr.eq-esi-3 td:first-child { border-left-color: #CA8A04; }
.eq-table tbody tr.eq-esi-4 td:first-child { border-left-color: #16A34A; }
.eq-table tbody tr.eq-esi-5 td:first-child { border-left-color: #2563EB; }
.eq-table .eq-esi-label {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
}

/* ── Patient Intake: ESI recommendation panel ── */
.esi-rec-panel {
    padding: 16px 20px;
    background: #1C2027;
    border-radius: 8px;
    border: 1px solid #5B6472;
}
.esi-rec-panel.esi-rec-1 { border-left: 4px solid #DC2626; }
.esi-rec-panel.esi-rec-2 { border-left: 4px solid #EA580C; }
.esi-rec-panel.esi-rec-3 { border-left: 4px solid #CA8A04; }
.esi-rec-panel.esi-rec-4 { border-left: 4px solid #16A34A; }
.esi-rec-panel.esi-rec-5 { border-left: 4px solid #2563EB; }
.esi-rec-panel .esi-level-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    line-height: 1;
}
.esi-rec-panel .esi-confidence {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    font-size: 1.1rem;
}
.esi-rec-1 .esi-level-num { color: #DC2626; }
.esi-rec-2 .esi-level-num { color: #EA580C; }
.esi-rec-3 .esi-level-num { color: #CA8A04; }
.esi-rec-4 .esi-level-num { color: #16A34A; }
.esi-rec-5 .esi-level-num { color: #2563EB; }

/* ── Deterioration Alerts styling by ESI level ── */
.det-alert {
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #E8E9EB;
    border: 1px solid #5B6472;
}
.det-alert-esi-1 { border-left: 5px solid #DC2626 !important; background: rgba(220, 38, 38, 0.18) !important; }
.det-alert-esi-2 { border-left: 5px solid #EA580C !important; background: rgba(234, 88, 12, 0.18) !important; }
.det-alert-esi-3 { border-left: 5px solid #CA8A04 !important; background: rgba(202, 138, 4, 0.18) !important; }
.det-alert-esi-4 { border-left: 5px solid #16A34A !important; background: rgba(22, 163, 74, 0.18) !important; }
.det-alert-esi-5 { border-left: 5px solid #2563EB !important; background: rgba(37, 99, 235, 0.18) !important; }
</style>
"""

def inject_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
