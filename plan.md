# PatientTriage.ai — Build Plan

This document tells you exactly what to build, file by file, function by
function. Follow it top to bottom. Do not invent features. Do not skip steps.

---

## What This Project Is

A Streamlit web app that helps emergency department triage nurses score patients
on the ESI 1–5 scale. It takes vital signs and a typed chief complaint, runs
them through a clinical rules engine and an LLM, and produces an ESI level with
a confidence percentage and a short justification the nurse can verify in
seconds. Patients enter a live priority queue that re-ranks by acuity and wait
time. The nurse can override any AI recommendation — overrides are logged. A
surge mode switches to the START mass-casualty protocol.

---

## Decisions Already Made

- **Language**: Python 3.10+
- **Frontend**: Streamlit (multi-page)
- **LLM**: Groq API (Llama 3 8B). Fallback: regex keyword matcher
- **Speech-to-text**: Stub only. Define the interface, raise NotImplementedError
- **Language support**: English only
- **Database**: SQLite via stdlib sqlite3
- **ML**: scikit-learn RandomForestClassifier
- **Data**: Kaggle Triagegeist dataset (100k records). Agent must write download
  instructions, not bundle the CSV
- **Validation**: Pydantic v2
- **Charts**: Plotly
- **Tests**: pytest
- **Demo video**: Not our problem

---

## Code Style

- No unnecessary comments. Only comment clinical thresholds or non-obvious math.
- No boilerplate headers, no `# -*- coding: utf-8 -*-`.
- No dead code, no commented-out blocks, no leftover TODOs.
- Type hints on every function signature.
- Early returns over deep nesting.
- Constants in config.py, never magic numbers inline.
- Imports: stdlib → third-party → local, one blank between groups.
- One blank line between functions, two between classes.
- Variable names in plain English: `patient_age` not `p_a`.

---

## Directory Structure

Create exactly these files:

```
PatientTriage/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── data/
│   ├── README.md
│   └── triage.db              ← auto-created at runtime
├── src/
│   ├── __init__.py            ← empty file
│   ├── models.py
│   ├── data_loader.py
│   ├── database.py
│   ├── clinical_rules.py
│   ├── risk_scorer.py
│   ├── llm_engine.py
│   ├── stt_engine.py
│   ├── queue_manager.py
│   └── surge_manager.py
├── pages/
│   ├── 1_📋_Patient_Intake.py
│   ├── 2_📊_Live_Queue.py
│   ├── 3_📝_Audit_Log.py
│   └── 4_🚨_Surge_Mode.py
└── tests/
    ├── test_clinical_rules.py
    ├── test_risk_scorer.py
    ├── test_queue_manager.py
    └── test_end_to_end.py
```

---

## Build Order

Build in this exact sequence. Each phase depends on the ones before it.

1. `config.py` + `src/models.py`
2. `src/database.py` + `src/data_loader.py` + `data/README.md`
3. `src/clinical_rules.py` + `tests/test_clinical_rules.py`
4. `src/llm_engine.py` + `src/risk_scorer.py` + `tests/test_risk_scorer.py`
5. `src/stt_engine.py` + `src/queue_manager.py` + `src/surge_manager.py` + `tests/test_queue_manager.py`
6. `app.py` + all 4 pages
7. `tests/test_end_to_end.py` + `README.md` + `requirements.txt`

---

## Phase 1: config.py + src/models.py

### config.py

This file holds every constant. No other file should contain magic numbers.

```python
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
```

For TODDLER and CHILD `sbp_low`, compute dynamically: `70 + (2 * age_years)`.
Store `None` in the dict and compute in `clinical_rules.py`.

### src/models.py

Define these Pydantic BaseModel classes. Use `from __future__ import annotations`.

**Patient**:
| Field | Type | Default |
|---|---|---|
| id | str | uuid4 hex |
| name | str | required |
| age | float | required (years, e.g., 0.5 for 6 months) |
| sex | Literal["M", "F"] | required |
| arrival_time | datetime | default_factory=datetime.utcnow |
| chief_complaint | str | "" |
| medical_history | str | "" (empty = zero-history) |
| status | Literal["WAITING", "IN_TREATMENT", "FAST_TRACK", "DISCHARGED"] | "WAITING" |
| current_esi | int \| None | None |

**VitalSigns**:
| Field | Type | Notes |
|---|---|---|
| patient_id | str | required |
| timestamp | datetime | default_factory=datetime.utcnow |
| heart_rate | int | bpm |
| respiratory_rate | int | breaths/min |
| spo2 | float | percentage 0–100 |
| systolic_bp | int | mmHg |
| diastolic_bp | int | mmHg |
| temperature | float | Celsius |
| pain_score | int | 0–10 |
| consciousness | Literal["A", "V", "P", "U"] | AVPU scale |
| supplemental_o2 | bool | False |

**ComplaintAnalysis**:
| Field | Type |
|---|---|
| red_flags | list[str] |
| symptom_onset_hours | float \| None |
| justification | str (≤10 words) |
| suggested_esi | int \| None |
| confidence | float (0.0–1.0) |

**TriageResult**:
| Field | Type |
|---|---|
| patient_id | str |
| timestamp | datetime |
| esi_level | int (1–5) |
| news2_score | int |
| confidence | float (0.0–1.0) |
| justification | str |
| red_flags | list[str] |
| is_override | bool |
| override_reason | str \| None |
| override_note | str \| None |

**AuditEntry**:
| Field | Type |
|---|---|
| id | str (uuid4) |
| timestamp | datetime |
| patient_id | str |
| clinician_id | str |
| event_type | Literal["SCORED", "ACCEPTED", "OVERRIDDEN", "REASSESSED"] |
| ai_esi | int |
| ai_confidence | float |
| ai_justification | str |
| final_esi | int |
| override_reason_code | str \| None |
| override_note | str \| None |
| dwell_seconds | float \| None |
| vitals_snapshot | dict |

---

## Phase 2: src/database.py + src/data_loader.py + data/README.md

### src/database.py

Use `sqlite3` stdlib. No SQLAlchemy.

**`init_db(db_path: str) -> sqlite3.Connection`**
Create these tables if not exist:

```sql
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age REAL NOT NULL,
    sex TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    chief_complaint TEXT DEFAULT '',
    medical_history TEXT DEFAULT '',
    status TEXT DEFAULT 'WAITING',
    current_esi INTEGER
);

CREATE TABLE IF NOT EXISTS vitals_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    heart_rate INTEGER,
    respiratory_rate INTEGER,
    spo2 REAL,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    temperature REAL,
    pain_score INTEGER,
    consciousness TEXT DEFAULT 'A',
    supplemental_o2 INTEGER DEFAULT 0,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS triage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    esi_level INTEGER NOT NULL,
    news2_score INTEGER,
    confidence REAL,
    justification TEXT,
    red_flags TEXT,
    is_override INTEGER DEFAULT 0,
    override_reason TEXT,
    override_note TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    clinician_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ai_esi INTEGER,
    ai_confidence REAL,
    ai_justification TEXT,
    final_esi INTEGER,
    override_reason_code TEXT,
    override_note TEXT,
    dwell_seconds REAL,
    vitals_snapshot TEXT
);
```

`audit_logs` is append-only. Never write UPDATE or DELETE for this table.

**Other functions** (all take `conn: sqlite3.Connection` as first arg):

- `insert_patient(conn, patient: Patient) -> None`
- `insert_vitals(conn, vitals: VitalSigns) -> None`
- `insert_triage_result(conn, result: TriageResult) -> None`
- `insert_audit_log(conn, entry: AuditEntry) -> None`
- `get_patient(conn, patient_id: str) -> dict | None`
- `get_latest_vitals(conn, patient_id: str) -> dict | None`
- `get_all_waiting_patients(conn) -> list[dict]` — WHERE status = 'WAITING'
- `update_patient_status(conn, patient_id: str, status: str) -> None`
- `update_patient_esi(conn, patient_id: str, esi: int) -> None`
- `get_audit_trail(conn, patient_id: str | None = None) -> list[dict]`
- `get_all_patients(conn) -> list[dict]`

All dict returns should use `sqlite3.Row` or manual dict conversion.
Store `red_flags` as JSON string. Store `vitals_snapshot` as JSON string.

### src/data_loader.py

**Purpose**: Load the Kaggle Triagegeist CSVs into SQLite for demo and model
training.

**`load_triagegeist(conn: sqlite3.Connection, csv_path: str, limit: int | None = None) -> int`**

1. Read CSV with pandas
2. For each row, create a Patient and VitalSigns from the CSV columns:
   - Map `patient_id` → Patient.id
   - Map `age` → Patient.age
   - Map `sex` → Patient.sex (normalize to "M"/"F")
   - Map `chief_complaint_raw` → Patient.chief_complaint (join from complaints CSV if separate file)
   - Map vitals columns directly to VitalSigns fields
   - Map comorbidity columns → Patient.medical_history (join non-zero comorbidity names as comma-separated string, or empty string if all zero = zero-history patient)
3. Insert into SQLite
4. Return count of loaded records

**`select_demo_cases(conn: sqlite3.Connection, n: int = 25) -> list[dict]`**

Select a diverse subset from loaded data:
- 2 ESI 1 cases
- 5 ESI 2 cases (ensure at least 1 female age>40 with cardiac-adjacent complaint, 1 age>65)
- 8 ESI 3 cases
- 6 ESI 4 cases
- 4 ESI 5 cases
- At least 3 patients with empty medical_history (zero-history)
- At least 2 patients age < 8 (pediatric)
- At least 2 patients age > 65 (geriatric)

Use SQL queries with WHERE clauses on `triage_acuity`, `age`, `medical_history`
to find qualifying rows. If exact matches aren't found, relax criteria and pick
closest matches.

**`get_training_data(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.Series]`**

Return (X, y) for sklearn training:
- X = DataFrame with columns: age, sex_encoded (M=0, F=1), heart_rate,
  respiratory_rate, spo2, systolic_bp, diastolic_bp, temperature, pain_score
- y = Series of triage_acuity (1–5)
- Drop rows with missing vitals

### data/README.md

Write exactly this content:

```markdown
# Dataset

This project uses the Triagegeist dataset from Kaggle.

## Download Instructions

1. Go to https://www.kaggle.com/datasets/laitinenfredriksson/triagegeist
2. Click "Download" (requires free Kaggle account)
3. Extract the ZIP into this `data/` directory
4. You should have `train.csv` and `test.csv` in this folder

## Attribution

Triagegeist dataset by laitinenfredriksson on Kaggle.
Modeled on MIMIC-IV-ED and NHAMCS statistical distributions.

## Fields Used

- patient_id, age, sex, arrival_mode
- systolic_bp, diastolic_bp, heart_rate, respiratory_rate,
  temperature_c, spo2, pain_score
- chief_complaint_raw (free-text)
- 25 binary comorbidity columns
- triage_acuity (ESI 1–5, our prediction target)
- disposition, ed_los_hours
```

---

## Phase 3: src/clinical_rules.py + tests

### src/clinical_rules.py

Import config values. Every threshold comes from `config.py`.

**`get_age_group(age_years: float) -> str`**
Loop through `config.AGE_GROUPS`. Return the matching key string.

**`get_pediatric_sbp_threshold(age_years: float) -> int`**
Return `70 + int(2 * age_years)`. Only valid for ages 1–10.

**`check_danger_zone(vitals: VitalSigns, age_years: float) -> tuple[bool, list[str]]`**

1. Get age group
2. Look up thresholds from `config.DANGER_ZONES[age_group]`
3. For TODDLER/CHILD, compute sbp_low dynamically with `get_pediatric_sbp_threshold`
4. Check each vital against thresholds. For each violation, append a string like
   `"HR 185 > 180"` to a triggers list
5. Return (len(triggers) > 0, triggers)

**`calculate_news2(vitals: VitalSigns) -> tuple[int, dict[str, int]]`**

1. Score each parameter using the tables in config:
   - respiratory_rate → NEWS2_RR
   - spo2 → NEWS2_SPO2
   - systolic_bp → NEWS2_SBP
   - heart_rate → NEWS2_HR
   - temperature → NEWS2_TEMP
   - consciousness → NEWS2_CONSCIOUSNESS
   - supplemental_o2 → 2 if True else 0
2. For each range table, iterate and return points for first matching range
3. Sum all scores
4. Return (total, {"rr": n, "spo2": n, "sbp": n, "hr": n, "temp": n, "consciousness": n, "o2": n})

**`calculate_shock_index(heart_rate: int, systolic_bp: int) -> tuple[float, bool]`**
```
si = heart_rate / systolic_bp
return (round(si, 2), si > 0.85)
```

**`check_red_flags(chief_complaint: str, age: float, sex: str, vitals: VitalSigns, has_diabetes: bool = False) -> list[str]`**

Check these patterns against the lowercased chief_complaint string:

1. **ATYPICAL_CARDIAC_FEMALE**: sex == "F" AND age >= 40 AND any keyword from
   `config.CARDIAC_FEMALE_KEYWORDS` found in complaint
2. **GERIATRIC_SEPSIS**: age >= 65 AND any keyword from `config.SEPSIS_KEYWORDS`
   found in complaint AND (vitals.temperature < 36.0 OR vitals.temperature > 38.0 OR shock_index > 0.85)
3. **PEDIATRIC_COMPENSATED_SHOCK**: age < 8 AND vitals.heart_rate above
   age-group hr_high AND vitals.systolic_bp >= age-appropriate sbp_low (normal BP
   despite tachycardia)
4. **SILENT_MI_DIABETIC**: has_diabetes AND ("diaphoresis" in complaint OR
   "sweating" in complaint OR "dyspnea" in complaint OR "shortness of breath" in
   complaint) AND "chest pain" NOT in complaint

Return list of matched flag name strings. Can be empty.

**`esi_decision_tree(patient: Patient, vitals: VitalSigns, resources_needed: int, danger_zone_result: tuple[bool, list[str]], red_flags: list[str]) -> tuple[int, str]`**

Implement exactly this logic:

```
Step A: Is patient unresponsive (consciousness == "U") or
        is any of these true: spo2 < 80, systolic_bp < 60, heart_rate < 30?
        → return (1, "Immediate life-saving intervention required")

Step B: Is consciousness "V" or "P"?
        OR pain_score >= 7?
        OR len(red_flags) > 0?
        OR danger_zone_result[0] is True?
        → return (2, generate justification from red_flags or danger_zone triggers)

Step C: resources_needed == 0 → return (5, "No resources needed")
        resources_needed == 1 → return (4, "Single resource needed")
        resources_needed >= 2 → go to Step D

Step D: danger_zone_result[0] is True → return (2, justification from triggers)
        else → return (3, "Stable, multiple resources needed")
```

**`generate_justification(esi: int, red_flags: list[str], danger_triggers: list[str], vitals: VitalSigns) -> str`**

Build a ≤10 word string. Examples:
- If ATYPICAL_CARDIAC_FEMALE in red_flags: `"Atypical cardiac: jaw pain + nausea in {age}F"`
- If GERIATRIC_SEPSIS in red_flags: `"Sepsis risk: temp {t} + confused + age {a}"`
- If danger triggers: join first 2 triggers like `"HR 185 high + SpO2 88 low"`
- If ESI 1: `"Critical: immediate intervention required"`
- Default: `"ESI {esi} based on vitals and complaint"`

Truncate to 10 words max.

### tests/test_clinical_rules.py

Write tests for:

1. `test_age_group_mapping` — verify each age maps correctly:
   - 0.01 → NEONATE, 0.1 → INFANT, 1.0 → TODDLER, 5 → CHILD, 30 → ADULT, 70 → GERIATRIC
2. `test_pediatric_sbp` — age 4 → threshold 78, age 6 → 82
3. `test_danger_zone_adult_tachycardia` — HR 110, adult → flagged
4. `test_danger_zone_adult_normal` — HR 80, RR 16, SpO2 98, SBP 120, temp 37 → not flagged
5. `test_danger_zone_geriatric_hypothermia` — temp 35.5 → flagged
6. `test_danger_zone_neonate_fever` — temp 38.5 → flagged
7. `test_news2_all_normal` — should score 0
8. `test_news2_high_risk` — HR 135, RR 26, SpO2 90, SBP 85, temp 39.5, consciousness "V" → score ≥ 7
9. `test_shock_index_normal` — HR 70, SBP 120 → SI 0.58, not flagged
10. `test_shock_index_high` — HR 110, SBP 95 → SI 1.16, flagged
11. `test_red_flag_atypical_cardiac` — female, age 55, complaint "jaw pain and nausea" → ATYPICAL_CARDIAC_FEMALE
12. `test_red_flag_geriatric_sepsis` — age 75, complaint "confused and lethargic", temp 35.5 → GERIATRIC_SEPSIS
13. `test_red_flag_silent_mi` — diabetic, complaint "profuse sweating and dyspnea", no "chest pain" → SILENT_MI_DIABETIC
14. `test_esi_level_1` — consciousness "U" → ESI 1
15. `test_esi_level_2_pain` — pain_score 8 → ESI 2
16. `test_esi_level_5` — resources 0 → ESI 5
17. `test_esi_level_4` — resources 1 → ESI 4
18. `test_esi_level_3` — resources 2, no danger zone → ESI 3
19. `test_esi_level_2_danger_zone` — resources 2, danger zone triggered → ESI 2

---

## Phase 4: src/llm_engine.py + src/risk_scorer.py + tests

### src/llm_engine.py

**`class LLMEngine`**

**`__init__(self, api_key: str | None = None)`**
- Store api_key. If None, read from env var `GROQ_API_KEY`.
- If still None, set `self.use_fallback = True`.
- Otherwise try importing `groq` and create client.

**`analyze_complaint(self, text: str, age: float, sex: str) -> ComplaintAnalysis`**
- If `use_fallback` or any exception → call `_keyword_fallback`
- Otherwise call `_groq_analyze`

**`_groq_analyze(self, text: str, age: float, sex: str) -> ComplaintAnalysis`**

Send this system prompt to Groq:

```
You are an emergency department triage assistant. Analyze the chief complaint
and return ONLY a JSON object with these fields:
- red_flags: list of clinical red flag strings (e.g., "Atypical cardiac presentation")
- symptom_onset_hours: number or null
- justification: string, MAX 10 words, clinical shorthand (e.g., "Sepsis risk: temp 101 + HR 115 + age 72")
- suggested_esi: integer 1-5 or null
- confidence: float 0.0-1.0

Patient: {age} year old {sex}.
Chief complaint: {text}

Return ONLY valid JSON, no markdown.
```

Parse the JSON response into a ComplaintAnalysis. If parsing fails, fall back
to `_keyword_fallback`.

**`_keyword_fallback(self, text: str, age: float, sex: str) -> ComplaintAnalysis`**

1. Lowercase the text
2. Check against each keyword list in config (CARDIAC_FEMALE_KEYWORDS,
   SEPSIS_KEYWORDS, STROKE_KEYWORDS, RESPIRATORY_KEYWORDS, TRAUMA_KEYWORDS)
3. Build red_flags list from matches
4. Set suggested_esi:
   - trauma keywords → 1
   - stroke keywords → 2
   - cardiac + female + age ≥ 40 → 2
   - sepsis + age ≥ 65 → 2
   - respiratory → 2
   - any other match → 3
   - no match → None
5. Set confidence = 0.5 for keyword fallback (lower than LLM)
6. Build a short justification from matched keywords
7. Return ComplaintAnalysis

### src/risk_scorer.py

**`class HybridRiskScorer`**

**`__init__(self, model_path: str | None = None)`**
- If model_path provided and file exists, load sklearn model with joblib
- Otherwise set `self.model = None`

**`train(self, X: pd.DataFrame, y: pd.Series) -> None`**
- Train a `RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")`
- Set `self.model` to the trained model
- Store `self.feature_names = X.columns.tolist()`

**`save_model(self, path: str) -> None`**
- Save with `joblib.dump`

**`score(self, patient: Patient, vitals: VitalSigns, complaint_analysis: ComplaintAnalysis, resources_needed: int) -> TriageResult`**

1. Run `check_danger_zone` → (is_danger, triggers)
2. Run `check_red_flags` → flags
3. Run `esi_decision_tree` → (rule_esi, rule_justification)
4. Run `calculate_news2` → (news2_score, breakdown)
5. If self.model is not None:
   - Build feature vector from vitals
   - Get `model.predict_proba` → class probabilities
   - `ml_confidence = max probability`
   - `ml_esi = class with max probability`
6. Else:
   - ml_confidence = 0.5
   - ml_esi = rule_esi

7. Merge LLM suggestion:
   - If complaint_analysis.suggested_esi is not None and complaint_analysis.confidence > 0.7:
     - Consider it as a third signal

8. Final ESI selection:
   - Start with rule_esi
   - If ml_esi < rule_esi (ML says more urgent): use ml_esi
   - If complaint_analysis.suggested_esi < rule_esi: use complaint suggested_esi
   - **Asymmetric escalation**: if final is ESI 3 and (ml_confidence < CONFIDENCE_ESCALATION_THRESHOLD or len(flags) > 0): escalate to ESI 2

9. Final confidence = weighted average:
   - `0.5 * rule_confidence + 0.3 * ml_confidence + 0.2 * complaint_confidence`
   - rule_confidence = 0.9 if danger zone or red flags triggered, else 0.7

10. Merge justification: prefer complaint_analysis.justification if LLM was
    used, else use rule_justification. Append red flag names.

11. Return TriageResult with all fields populated.

**`get_feature_importance(self) -> dict[str, float]`**
- If model exists, return dict of feature_name → importance
- Else return empty dict

### tests/test_risk_scorer.py

1. `test_escalation_under_uncertainty` — mock model with confidence 0.6 on ESI 3 → should produce ESI 2
2. `test_red_flag_forces_esi_2` — patient with ATYPICAL_CARDIAC_FEMALE flag, rules say ESI 3 → output ESI 2
3. `test_esi_1_not_overridden` — rule says ESI 1 → output stays ESI 1 regardless of ML
4. `test_confidence_range` — output confidence always between 0.0 and 1.0
5. `test_justification_not_empty` — every TriageResult has non-empty justification
6. `test_justification_max_10_words` — justification has ≤ 10 words

---

## Phase 5: src/stt_engine.py + src/queue_manager.py + src/surge_manager.py

### src/stt_engine.py

This is a **stub**. Minimal code.

```python
class STTEngine:
    def is_available(self) -> bool:
        return False

    def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError(
            "Speech-to-text not implemented. Install faster-whisper and update this module."
        )
```

That's the entire file. Nothing else.

### src/queue_manager.py

**`calculate_priority(esi_level: int, wait_minutes: float, deterioration_bonus: float = 0) -> float`**

```python
base = config.ACUITY_BASE[esi_level]
factor = config.ACUITY_WAIT_FACTOR[esi_level]
return base + (wait_minutes * factor) + deterioration_bonus
```

**`get_ranked_queue(conn: sqlite3.Connection) -> list[dict]`**

1. Call `get_all_waiting_patients(conn)`
2. For each patient, get latest vitals and latest triage result
3. Calculate wait_minutes = (now - arrival_time).total_seconds() / 60
4. Calculate priority score
5. Sort descending by priority (highest = most urgent)
6. Return list of dicts with: patient fields + wait_minutes + priority_score + esi_level

**`check_deterioration_alerts(conn: sqlite3.Connection) -> list[dict]`**

1. Get all waiting patients with their ESI level and arrival_time
2. For each, compute wait_minutes
3. If wait_minutes > `config.DETERIORATION_THRESHOLDS_MIN[esi_level]`:
   - Add to alerts list with patient info and how many minutes overdue
4. Return alerts list sorted by urgency (ESI 1 first, then by overdue minutes descending)

### src/surge_manager.py

**`class SurgeManager`**

**`__init__(self)`**
- `self.active = False`
- `self.categories: dict[str, list[str]]` = {"RED": [], "YELLOW": [], "GREEN": [], "BLACK": []}

**`activate(self) -> None`**: set active = True, clear categories

**`deactivate(self) -> None`**: set active = False, clear categories

**`is_active(self) -> bool`**: return self.active

**`start_triage(self, patient_id: str, can_walk: bool, respiratory_rate: int | None, has_radial_pulse: bool, follows_commands: bool, breathing_after_airway: bool) -> str`**

Implement START protocol exactly:

```
if can_walk:
    category = "GREEN"
elif respiratory_rate is None or respiratory_rate == 0:
    if not breathing_after_airway:
        category = "BLACK"
    else:
        category = "RED"
elif respiratory_rate > 30:
    category = "RED"
elif not has_radial_pulse:
    category = "RED"
elif not follows_commands:
    category = "RED"
else:
    category = "YELLOW"
```

Add patient_id to self.categories[category]. Return category.

**`get_stats(self) -> dict[str, int]`**
Return count per category.

**`get_all_categorized(self) -> dict[str, list[str]]`**
Return self.categories.

### tests/test_queue_manager.py

1. `test_esi1_ranks_above_esi2` — ESI 1 patient at 0 min wait has higher priority than ESI 2 at 0 min
2. `test_wait_time_increases_priority` — ESI 3 patient at 60 min wait has higher priority than ESI 3 at 5 min
3. `test_esi2_alert_at_11_min` — ESI 2 patient waiting 11 minutes triggers deterioration alert
4. `test_esi3_no_alert_at_20_min` — ESI 3 patient waiting 20 minutes does NOT trigger alert
5. `test_esi3_alert_at_31_min` — ESI 3 patient waiting 31 minutes DOES trigger alert
6. `test_start_walking_is_green` — can_walk=True → GREEN
7. `test_start_apneic_no_recovery_is_black` — can_walk=False, rr=0, breathing_after_airway=False → BLACK
8. `test_start_high_rr_is_red` — rr=35 → RED
9. `test_start_no_pulse_is_red` — has_radial_pulse=False → RED
10. `test_start_follows_commands_is_yellow` — rr=20, pulse=True, follows_commands=True → YELLOW

---

## Phase 6: app.py + Streamlit Pages

### app.py

```python
import streamlit as st
from src.database import init_db
import config

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="🏥",
    layout="wide",
)

conn = init_db(config.DB_PATH)
st.session_state.setdefault("db_conn", conn)
st.session_state.setdefault("surge_active", False)

st.sidebar.title("🏥 PatientTriage.ai")
st.sidebar.caption("AI-Assisted ED Triage Decision Support")
st.sidebar.divider()
st.sidebar.warning("DEMO — Public Dataset — Not for Clinical Use")

# Show ED stats in sidebar
# Query patient counts by ESI level and status from DB
# Display with st.sidebar.metric
```

The main page should show a brief welcome/overview. Keep it short.

### pages/1_📋_Patient_Intake.py

Two modes:
1. **Manual entry** — nurse types vitals and complaint
2. **Load from dataset** — select a pre-loaded patient from the database

**Manual entry form** (use `st.form`):
- Left column: age (number_input), sex (selectbox M/F), consciousness (selectbox AVPU)
- Middle column: HR, RR, SpO2, SBP, DBP (all number_input with reasonable defaults and min/max)
- Right column: temperature, pain_score (slider 0–10), supplemental O2 (checkbox)
- Below: chief_complaint (text_area), medical_history (text_area, label includes "leave blank if unknown")
- Below: resources_needed (radio: "None (exam only)", "One (e.g., X-ray)", "Two or more (labs + imaging)")
- Submit button

**On submit**:
1. Create Patient and VitalSigns from form data
2. Insert into DB
3. Run LLMEngine.analyze_complaint
4. Run HybridRiskScorer.score
5. Display results in a colored box:
   - ESI level as a large colored badge (1=🔴, 2=🟠, 3=🟡, 4=🟢, 5=🔵)
   - Confidence as a progress bar
   - Justification in bold large text
   - Red flags in st.error boxes
   - NEWS2 breakdown in an expander
6. Two buttons: "✅ Accept" and "🔄 Override"
7. If Accept: log audit entry with event_type ACCEPTED
8. If Override: show selectbox with OVERRIDE_REASONS + text_input for note,
   then log audit entry with event_type OVERRIDDEN and the nurse's ESI choice (number_input 1–5)

**Load from dataset**:
- Selectbox of patient names/IDs from DB
- On select, auto-fill the form fields
- Same scoring flow as manual entry

### pages/2_📊_Live_Queue.py

Use `@st.fragment(run_every=5)` to auto-refresh the queue section.

1. Call `get_ranked_queue(conn)` → list of patients
2. Display as a dataframe/table with columns:
   - Rank (#)
   - Patient Name
   - ESI Level (use colored text or emoji: 1=🔴, 2=🟠, 3=🟡, 4=🟢, 5=🔵)
   - Chief Complaint (truncated to 50 chars)
   - Wait Time (formatted as "Xm" or "Xh Ym")
   - Priority Score
   - Status
3. Call `check_deterioration_alerts(conn)` → list
4. For each alert, show `st.warning` or `st.error`:
   - `"⚠️ Patient {name} (ESI {esi}) waiting {wait}min — exceeds {threshold}min safe limit"`
5. Below the table, show summary metrics:
   - Total waiting patients
   - Count per ESI level (use st.columns with st.metric)
   - Average wait time per ESI level

### pages/3_📝_Audit_Log.py

1. Filters at top: patient name (text_input), event type (multiselect), date range (date_input)
2. Query `get_audit_trail(conn)` with filters
3. Display as a table
4. For OVERRIDDEN entries, show extra columns: AI ESI vs Final ESI, reason code, note, dwell time
5. Download CSV button using `st.download_button` with the dataframe as CSV

### pages/4_🚨_Surge_Mode.py

1. Big toggle button at top: "Activate Surge Mode" / "Deactivate Surge Mode"
   - Uses `st.session_state.surge_active`
   - When activated, show `st.error("🚨 SURGE MODE ACTIVE — START Protocol")`

2. When active, show the START triage form:
   - Patient selector (from DB) or manual name entry
   - Radio: "Can the patient walk?" (Yes/No)
   - If No: number_input for respiratory rate
   - If RR is 0: checkbox "Breathing after airway opening?"
   - If RR > 0: checkbox "Radial pulse present?", checkbox "Follows simple commands?"
   - Submit → call surge_manager.start_triage → show result as colored card

3. Below form, show 4 columns (one per START category):
   - 🔴 IMMEDIATE (Red): count + patient list
   - 🟡 DELAYED (Yellow): count + patient list
   - 🟢 MINOR (Green): count + patient list
   - ⚫ EXPECTANT (Black): count + patient list

4. "Simulate 3× Surge" button:
   - Randomly sample 30 patients from the dataset
   - Auto-generate plausible START assessment values for each
   - Run start_triage for each
   - Display results in the 4 columns
   - Show a Plotly bar chart of category distribution

---

## Phase 7: tests/test_end_to_end.py + README.md + requirements.txt

### tests/test_end_to_end.py

This file tests the full pipeline on real dataset records.

1. `test_score_20_patients` — load 20 diverse patients from the dataset,
   run HybridRiskScorer.score on each, assert all return valid ESI 1–5 and
   confidence 0.0–1.0
2. `test_ambiguous_case_has_red_flags` — find a patient with an ambiguous
   complaint (female 40+ with GI symptoms), verify red_flags is non-empty
3. `test_pediatric_case` — score a patient age < 8, verify age-appropriate
   thresholds were applied
4. `test_geriatric_case` — score a patient age > 65, verify geriatric thresholds
5. `test_zero_history_patient` — score a patient with empty medical_history,
   verify it still produces a valid result
6. `test_override_logged` — simulate an override, query audit_logs, verify
   the entry contains all required fields
7. `test_surge_reclassification` — activate surge, run start_triage on 5
   patients, verify each gets a valid START category
8. `test_queue_ordering` — insert 5 patients with different ESI levels,
   verify get_ranked_queue returns them in correct order

### requirements.txt

```
streamlit>=1.35.0
scikit-learn>=1.4.0
pydantic>=2.0.0
pandas>=2.2.0
numpy>=1.26.0
groq>=0.9.0
plotly>=5.20.0
pytest>=8.0.0
joblib>=1.3.0
```

### README.md

Follow the format from instructions.md (Drupal-style). Write these sections:

**# PatientTriage.ai**
- 2-paragraph introduction: what it does, why it matters
- Link to the GitHub repo

**## Table of Contents**

**## Requirements**
- Python 3.10+
- Groq API key (free at console.groq.com)
- Kaggle account (to download dataset)

**## Installation**
```
git clone <repo>
cd PatientTriage
pip install -r requirements.txt
```

**## Configuration**
- Set GROQ_API_KEY env variable
- Download dataset (point to data/README.md)
- Run data loader: `python -c "from src.data_loader import ...; ..."`

**## Usage**
```
streamlit run app.py
```
- Describe each tab briefly

**## Architecture**
- Paste the mermaid diagram or describe the data flow in prose
- List the tech stack table

**## Clinical Methodology**
- ESI 1–5 decision tree summary
- NEWS2 scoring
- Safety-first escalation policy
- START protocol for surge

**## Dataset**
- Attribution to Triagegeist
- Brief description

**## Safety & Compliance**
- Not for clinical use disclaimer
- HIPAA awareness (public dataset, no PHI)
- FDA Non-Device CDS criteria summary

**## Testing**
```
pytest tests/ -v
```

**## Troubleshooting**
- "Groq API key not set" → set env var or app uses keyword fallback
- "Dataset not found" → follow data/README.md download steps

---

## Final Checklist

Before calling the project done, verify:

- [ ] `streamlit run app.py` launches without errors
- [ ] All 4 tabs render and are functional
- [ ] Manual patient intake → scoring → result display works
- [ ] Loading a dataset patient → scoring works
- [ ] Override flow → audit log entry appears in Audit Log tab
- [ ] Live Queue shows patients ranked by priority
- [ ] Deterioration alerts appear for long-waiting patients
- [ ] Surge Mode activates and START triage works
- [ ] 3× surge simulation runs and shows category breakdown
- [ ] `pytest tests/ -v` passes all tests
- [ ] README.md is complete and follows the format
- [ ] No hardcoded API keys in source code
- [ ] No unnecessary comments or dead code
