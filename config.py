import os
import sys

pkg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".packages"))
if os.path.exists(pkg_path) and pkg_path not in sys.path:
    sys.path.insert(0, pkg_path)

# --- Groq API ---
GROQ_MODEL = "llama3-8b-8192"
GROQ_TIMEOUT = 10          # seconds
GROQ_MAX_TOKENS = 512

# --- Database ---
DB_PATH = "data/triage.db"

# --- Age Groups (enum-like) ---
# Use these strings as keys everywhere
AGE_GROUPS = {
    "NEONATE":  (0, 0.077),      # 0 to 28 days (28/365)
    "INFANT":   (0.077, 0.25),   # 28 days to 3 months
    "TODDLER":  (0.25, 3),       # 3 months to 3 years
    "CHILD":    (3, 8),          # 3 to 8 years
    "ADULT":    (8, 65),         # 8 to 65 years
    "GERIATRIC": (65, 200),      # 65+
}

# --- Danger Zone Vital Thresholds ---
# Format: (hr_high, hr_low, rr_high, rr_low, spo2_low, sbp_low, temp_high, temp_low)
DANGER_ZONES = {
    "NEONATE":   {"hr_high": 180, "hr_low": 100, "rr_high": 50, "rr_low": 25, "spo2_low": 92, "sbp_low": 60,  "temp_high": 38.0, "temp_low": None},
    "INFANT":    {"hr_high": 180, "hr_low": 90,  "rr_high": 50, "rr_low": 20, "spo2_low": 92, "sbp_low": 70,  "temp_high": 38.0, "temp_low": None},
    "TODDLER":   {"hr_high": 160, "hr_low": None,"rr_high": 40, "rr_low": None,"spo2_low": 92, "sbp_low": None,"temp_high": 39.0, "temp_low": None},
    "CHILD":     {"hr_high": 140, "hr_low": None,"rr_high": 30, "rr_low": None,"spo2_low": 92, "sbp_low": None,"temp_high": 39.0, "temp_low": None},
    "ADULT":     {"hr_high": 100, "hr_low": 50,  "rr_high": 20, "rr_low": 10, "spo2_low": 92, "sbp_low": 90,  "temp_high": 40.0, "temp_low": 35.0},
    "GERIATRIC": {"hr_high": 90,  "hr_low": None,"rr_high": 20, "rr_low": None,"spo2_low": 92, "sbp_low": 100, "temp_high": 38.0, "temp_low": 36.0},
}

# --- NEWS2 Scoring Tables ---
# Each param maps value ranges to points (0–3)
# Format: list of (low, high, points) checked in order; first match wins
NEWS2_RR = [(25, 999, 3), (21, 24, 2), (9, 11, 1), (12, 20, 0), (0, 8, 3)]
NEWS2_SPO2 = [(96, 100, 0), (94, 95, 1), (92, 93, 2), (0, 91, 3)]
NEWS2_SBP = [(220, 999, 3), (0, 90, 3), (91, 100, 2), (101, 110, 1), (111, 219, 0)]
NEWS2_HR = [(131, 999, 3), (111, 130, 2), (91, 110, 1), (51, 90, 0), (41, 50, 1), (0, 40, 3)]
NEWS2_TEMP = [(39.1, 99, 2), (38.1, 39.0, 1), (36.1, 38.0, 0), (35.1, 36.0, 1), (0, 35.0, 3)]
NEWS2_CONSCIOUSNESS = {"A": 0, "V": 3, "P": 3, "U": 3}

# --- Queue Parameters ---
ACUITY_BASE = {1: 1000, 2: 500, 3: 200, 4: 50, 5: 10}
ACUITY_WAIT_FACTOR = {1: 10, 2: 5, 3: 2, 4: 0.5, 5: 0.1}
DETERIORATION_THRESHOLDS_MIN = {1: 0, 2: 10, 3: 30, 4: 120, 5: 240}

# --- Escalation ---
CONFIDENCE_ESCALATION_THRESHOLD = 0.70  # below this, ESI 3 → ESI 2

# --- Override Reason Codes ---
OVERRIDE_REASONS = [
    "CLINICAL_CUES_NOT_IN_VITALS",
    "ATYPICAL_PRESENTATION",
    "PATIENT_PAIN_SEVERITY",
    "KNOWN_COMORBIDITY",
    "RAPID_DECOMPENSATION",
    "AI_OVERESTIMATED",
    "BASELINE_CHRONIC",
]

# --- Red Flag Patterns (for keyword fallback) ---
CARDIAC_FEMALE_KEYWORDS = ["jaw pain", "epigastric", "nausea", "fatigue", "back pain", "indigestion"]
SEPSIS_KEYWORDS = ["confused", "confusion", "lethargic", "lethargy", "not acting right", "altered mental"]
STROKE_KEYWORDS = ["slurred speech", "facial droop", "arm weakness", "sudden headache", "vision loss"]
RESPIRATORY_KEYWORDS = ["shortness of breath", "dyspnea", "wheezing", "cannot breathe", "choking"]
TRAUMA_KEYWORDS = ["gunshot", "stabbing", "fall from height", "car accident", "mva", "crush injury"]

# --- ML Model Path ---
MODEL_PATH = "data/triage_model.joblib"

