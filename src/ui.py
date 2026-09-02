import streamlit as st

# ── Single source of truth: ESI palette ──────────────────────────────────────
ESI_COLORS = {
    1: {"border": "#DC2626", "bg": "rgba(220,38,38,0.15)",  "text": "#F87171"},
    2: {"border": "#EA580C", "bg": "rgba(234,88,12,0.15)",  "text": "#FB923C"},
    3: {"border": "#CA8A04", "bg": "rgba(202,138,4,0.15)",  "text": "#FCD34D"},
    4: {"border": "#16A34A", "bg": "rgba(22,163,74,0.15)",  "text": "#4ADE80"},
    5: {"border": "#2563EB", "bg": "rgba(37,99,235,0.15)",  "text": "#60A5FA"},
}

ESI_NAMES = {
    1: "ESI 1 — Resuscitation (Immediate)",
    2: "ESI 2 — Emergent (High Risk)",
    3: "ESI 3 — Urgent (Multiple Resources)",
    4: "ESI 4 — Less Urgent (One Resource)",
    5: "ESI 5 — Non-Urgent (No Resources)",
}

ESI_SHORT = {
    1: "RESUS",
    2: "EMERGENT",
    3: "URGENT",
    4: "LESS URGENT",
    5: "NON-URGENT",
}

# START protocol category colors
START_COLORS = {
    "RED":    {"border": "#DC2626", "bg": "rgba(220,38,38,0.15)",  "text": "#F87171",  "label": "IMMEDIATE"},
    "YELLOW": {"border": "#CA8A04", "bg": "rgba(202,138,4,0.15)",  "text": "#FCD34D",  "label": "DELAYED"},
    "GREEN":  {"border": "#16A34A", "bg": "rgba(22,163,74,0.15)",  "text": "#4ADE80",  "label": "MINOR"},
    "BLUE":   {"border": "#2563EB", "bg": "rgba(37,99,235,0.15)",  "text": "#60A5FA",  "label": "EXPECTANT"},
    "BLACK":  {"border": "#2563EB", "bg": "rgba(37,99,235,0.15)",  "text": "#60A5FA",  "label": "EXPECTANT"},
}

# Audit event type colors
AUDIT_EVENT_COLORS = {
    "SCORED":     {"border": "#5B6472", "bg": "rgba(91,100,114,0.12)",  "text": "#94A3B8"},
    "ACCEPTED":   {"border": "#16A34A", "bg": "rgba(22,163,74,0.12)",   "text": "#4ADE80"},
    "OVERRIDDEN": {"border": "#CA8A04", "bg": "rgba(202,138,4,0.12)",   "text": "#FCD34D"},
    "REASSESSED": {"border": "#2563EB", "bg": "rgba(37,99,235,0.12)",   "text": "#60A5FA"},
}

# ── Helper: format wait minutes ───────────────────────────────────────────────
def format_wait_time(mins: float) -> str:
    if mins < 60:
        return f"{int(mins)}m"
    hours = int(mins // 60)
    rem = int(mins % 60)
    return f"{hours}h {rem}m"


# ── Helper: ESI badge HTML ────────────────────────────────────────────────────
def esi_badge_html(esi: int) -> str:
    c = ESI_COLORS.get(esi, {"border": "#5B6472", "bg": "rgba(91,100,114,0.15)", "text": "#E8E9EB"})
    short = ESI_SHORT.get(esi, f"ESI {esi}")
    return (
        f'<span style="background:{c["bg"]};border:1px solid {c["border"]};'
        f'color:{c["text"]};border-radius:4px;padding:2px 7px;'
        f'font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;'
        f'font-weight:600;letter-spacing:0.04em;white-space:nowrap;">'
        f'ESI {esi} <span style="opacity:0.7;font-size:0.68rem;">{short}</span>'
        f'</span>'
    )


# ── SVG Icons (monochrome, 22×22) ─────────────────────────────────────────────
ICON_INTAKE = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="2" width="6" height="4" rx="1"/>
  <path d="M9 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-3"/>
  <line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>
  <line x1="9" y1="8" x2="15" y2="8"/>
</svg>"""

ICON_QUEUE = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
  <line x1="8" y1="18" x2="21" y2="18"/>
  <circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>
</svg>"""

ICON_AUDIT = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
  <polyline points="10 9 9 9 8 9"/>
</svg>"""

ICON_SURGE = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
</svg>"""


# ── CSS ───────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base typography ── */
html, body, p, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText {
    font-family: 'Inter', 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem;
}

/* ── Metric containers ── */
div[data-testid="stMetricContainer"] {
    background: #1C2027 !important;
    border: 1px solid #2A303B !important;
    border-radius: 8px !important;
    padding: 15px 20px !important;
}

/* ── Alerts: flat, no blur ── */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    box-shadow: none !important;
}

/* ── Monospace utility ── */
.mono-data, .eq-mono {
    font-family: 'IBM Plex Mono', monospace !important;
    font-variant-numeric: tabular-nums !important;
}

/* ── Sidebar ESI strip ── */
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
    border-radius: 0 4px 4px 0;
    transition: background 0.2s ease;
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
.esi-strip-item.esi-empty { border-left-color: #2A303B; opacity: 0.45; }

/* Sidebar alert glow when active alerts exist */
.sidebar-alert-active .esi-strip-item.esi-1,
.sidebar-alert-active .esi-strip-item.esi-2 {
    background: rgba(220, 38, 38, 0.08);
}

/* ── Landing nav cards ── */
.nav-card {
    background: #1C2027;
    border: 1px solid #2A303B;
    border-radius: 10px;
    padding: 20px 18px 16px;
    height: 100%;
    transition: border-color 0.18s ease, background 0.18s ease;
}
.nav-card:hover {
    border-color: #5B6472;
    background: #20262F;
}
.nav-card-icon {
    color: #5B6472;
    margin-bottom: 10px;
    display: block;
    line-height: 1;
}
.nav-card-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #E8E9EB;
    margin: 0 0 6px 0;
}
.nav-card-desc {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #5B6472;
    line-height: 1.5;
    margin: 0 0 14px 0;
}

/* ── Patient queue cards ── */
.queue-section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #5B6472;
    padding: 6px 0 8px;
    border-bottom: 1px solid #2A303B;
    margin-bottom: 10px;
}
.patient-card {
    background: #1C2027;
    border: 1px solid #2A303B;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 4px solid transparent;
    transition: border-color 0.15s ease, background 0.15s ease;
}
.patient-card:hover { background: #20262F; }
.patient-card.esi-1 { border-left-color: #DC2626; }
.patient-card.esi-2 { border-left-color: #EA580C; }
.patient-card.esi-3 { border-left-color: #CA8A04; }
.patient-card.esi-4 { border-left-color: #16A34A; }
.patient-card.esi-5 { border-left-color: #2563EB; }
.patient-card-name {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    color: #E8E9EB;
    margin-bottom: 4px;
}
.patient-card-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: #5B6472;
    line-height: 1.5;
}
.patient-card-complaint {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #94A3B8;
    margin-top: 4px;
    font-style: italic;
}
.patient-card-wait {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    font-size: 0.85rem;
    color: #E8E9EB;
    font-weight: 500;
}

/* ── Live update indicator ── */
.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #5B6472;
}
.live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #16A34A;
    display: inline-block;
    animation: live-pulse 2.5s ease-in-out infinite;
}
@keyframes live-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.35; }
}

/* ── Avg wait chips ── */
.wait-chip {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 14px;
    background: #1C2027;
    border: 1px solid #2A303B;
    border-radius: 6px;
    margin-right: 6px;
    margin-bottom: 6px;
}
.wait-chip-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #5B6472;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.wait-chip-value {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    font-size: 1rem;
    font-weight: 600;
    color: #E8E9EB;
    margin-top: 2px;
}

/* ── Audit timeline ── */
.timeline-entry {
    border-left: 3px solid transparent;
    border-radius: 0 8px 8px 0;
    margin-bottom: 6px;
}
.timeline-entry.evt-SCORED     { border-left-color: #5B6472; }
.timeline-entry.evt-ACCEPTED   { border-left-color: #16A34A; }
.timeline-entry.evt-OVERRIDDEN { border-left-color: #CA8A04; }
.timeline-entry.evt-REASSESSED { border-left-color: #2563EB; }
.timeline-ts {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #5B6472;
    white-space: nowrap;
}
.timeline-evt-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 6px;
    border-radius: 3px;
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

/* ── Vitals display table ── */
.vitals-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
}
.vitals-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #2A303B;
    color: #94A3B8;
    vertical-align: middle;
}
.vitals-table td:last-child {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    color: #E8E9EB;
    font-weight: 500;
    text-align: right;
}
.vitals-table tr:last-child td { border-bottom: none; }

/* ── Deterioration Alerts ── */
.det-alert {
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #E8E9EB;
    border: 1px solid #2A303B;
}
.det-alert-esi-1 { border-left: 5px solid #DC2626 !important; background: rgba(220,38,38,0.18) !important; }
.det-alert-esi-2 { border-left: 5px solid #EA580C !important; background: rgba(234,88,12,0.18) !important; }
.det-alert-esi-3 { border-left: 5px solid #CA8A04 !important; background: rgba(202,138,4,0.18) !important; }
.det-alert-esi-4 { border-left: 5px solid #16A34A !important; background: rgba(22,163,74,0.18) !important; }
.det-alert-esi-5 { border-left: 5px solid #2563EB !important; background: rgba(37,99,235,0.18) !important; }

/* ── Surge category blocks ── */
.surge-cat-block {
    border-radius: 8px;
    border: 1px solid #2A303B;
    border-top: 4px solid transparent;
    padding: 16px 14px 12px;
    background: #1C2027;
    min-height: 100px;
}
.surge-cat-block.cat-RED    { border-top-color: #DC2626; }
.surge-cat-block.cat-YELLOW { border-top-color: #CA8A04; }
.surge-cat-block.cat-GREEN  { border-top-color: #16A34A; }
.surge-cat-block.cat-BLUE   { border-top-color: #2563EB; }
.surge-cat-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #5B6472;
    margin-bottom: 4px;
}
.surge-cat-count {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 10px;
}
.surge-cat-count.cat-RED    { color: #F87171; }
.surge-cat-count.cat-YELLOW { color: #FCD34D; }
.surge-cat-count.cat-GREEN  { color: #4ADE80; }
.surge-cat-count.cat-BLUE   { color: #60A5FA; }
.surge-pid {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #5B6472;
    margin-bottom: 2px;
}

/* ── Tablet Optimizations ── */
/* Touch Targets for Streamlit Widgets */
div.stButton > button,
div[data-baseweb="select"] > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stRadio"] label {
    min-height: 48px !important;
    font-size: 1.05rem !important;
}

div[data-testid="stRadio"] label {
    padding-top: 8px !important;
    padding-bottom: 8px !important;
}

/* Increase badge size and wait chip size slightly */
.esi-badge {
    padding: 4px 10px !important;
    font-size: 0.85rem !important;
}
.wait-chip-value {
    font-size: 1.1rem !important;
}

/* Sidebar toggle */
button[data-testid="collapsedControl"] {
    min-height: 48px !important;
    min-width: 48px !important;
}
</style>
"""


def inject_custom_css() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
