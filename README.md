# PatientTriage.ai

PatientTriage.ai is an intelligent clinical decision-support system designed
to assist emergency department (ED) triage nurses in accurately assigning
Emergency Severity Index (ESI) levels. By combining age-adjusted physiological
danger zones, the National Early Warning Score (NEWS2), targeted red-flag
clinical heuristics, and a Large Language Model (LLM) for complaint analysis,
the platform delivers rapid, transparent, and defensible triage recommendations
with high-confidence clinical justifications in under ten words.

In fast-paced, high-stress emergency environments, cognitive fatigue and
incomplete data often lead to catastrophic under-triage — such as overlooking
atypical cardiac presentations in women, silent myocardial infarctions in
diabetic patients, or compensated shock in pediatrics. PatientTriage.ai
addresses these challenges through asymmetric safety-first escalation, a
dynamic waiting room priority queue, immutable audit logging, and rapid
switching into the START protocol during mass-casualty surges.

For source code, issue tracking, and contributions, visit the
[PatientTriage GitHub Repository](https://github.com/AgroKING/PatientTriage).


## Table of contents

- Requirements
- Installation
- Configuration
- Usage
- Architecture
- Clinical methodology
- Dataset
- ML model training
- Safety & compliance
- Testing
- Troubleshooting
- Maintainers


## Requirements

This project requires the following tools and services:

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management
- [Groq API Key](https://console.groq.com/) for high-speed Llama-3 inference
  (optional — regex fallback activates automatically if omitted)
- Kaggle account to obtain the optional 100k-record Triagegeist dataset
  (optional — 21 built-in demo patients are seeded automatically on first run)


## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/AgroKING/PatientTriage.git
    cd PatientTriage
    ```
1. Create a virtual environment and install dependencies:
    ```bash
    uv venv
    uv pip install -r requirements.txt
    ```
    Or with pip:
    ```bash
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt   # Windows
    # source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
    ```


## Configuration

1. Set up your Groq API key (optional — keyword fallback is used if omitted):
    ```bash
    # Windows PowerShell
    $env:GROQ_API_KEY = "gsk_your_groq_api_key_here"

    # macOS / Linux
    export GROQ_API_KEY="gsk_your_groq_api_key_here"
    ```
1. The SQLite database and the 21 demo patients are seeded automatically on
   first launch — no manual setup required.
1. To use the full 100k-record Triagegeist dataset, follow the instructions in
   [data/README.md](data/README.md), then run the model training script:
    ```bash
    .venv\Scripts\python train_model.py    # Windows
    # python train_model.py               # macOS/Linux
    ```


## Usage

Launch the multi-page Streamlit application:

```bash
.venv\Scripts\streamlit run app.py    # Windows
# streamlit run app.py               # macOS/Linux
```

The application provides four operational modules accessible from the sidebar:

- **Patient intake**: Manual vitals and chief complaint entry, or load a
  pre-seeded patient from the database. Includes an optional speech-to-text
  recorder for hands-free complaint capture. Produces instant ESI scoring,
  confidence bar, NEWS2 breakdown, and clinician Accept/Override controls.
- **Live queue**: Real-time dynamic queue ranking combining ESI acuity and
  elapsed wait time, with automatic deterioration alerts for overdue patients.
  Auto-refreshes every 5 seconds.
- **Audit log**: Tamper-evident append-only trail capturing all AI suggestions,
  clinician overrides, reason codes, and decision dwell times. One-click CSV
  export.
- **Surge mode**: Toggle Simple Triage and Rapid Treatment (START) protocol
  for mass-casualty events. Includes a 3× volume disaster simulation with
  Plotly category distribution chart.


## Architecture

PatientTriage.ai employs a layered, safety-centric software architecture:

```
+-------------------------------------------------------------------------+
|                         Streamlit Web Interface                         |
|  [Patient Intake]     [Live Queue]     [Audit Log]     [Surge Mode]     |
+--------------------+-------------------+---------------+----------------+
                     |                   |               |
                     v                   v               v
+-------------------------------------------------------------------------+
|                              Core Engines                               |
|  - Clinical Rules Engine (NEWS2, Danger Zones, Pediatric Thresholds)   |
|  - Hybrid Risk Scorer (RandomForestClassifier + Heuristic Rules)       |
|  - LLM Engine (Groq Llama 3 8B with Regex Keyword Fallback)            |
|  - Dynamic Queue Manager (Wait-time Acuity Weighting & Alerts)          |
|  - Surge Manager (START Mass-Casualty Protocol)                         |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       SQLite Persistence Layer                          |
|    - patients   - vitals_history   - triage_results   - audit_logs      |
+-------------------------------------------------------------------------+
```


### Technology stack

| Component | Technology | Rationale |
|---|---|---|
| Runtime | Python 3.10+ | Standard biomedical ML & data ecosystem |
| Web UI | Streamlit | Rapid multi-page clinician-facing interface |
| Validation | Pydantic v2 | Strict schema validation on medical records |
| Inference | Groq API (Llama 3 8B) | Ultra-low latency (<500ms) NLP analysis |
| ML Scorer | scikit-learn | Fast, interpretable Random Forest classification |
| Storage | SQLite3 | Lightweight, serverless relational database |
| Visualization | Plotly | Dynamic charting and surge analytics |
| Testing | pytest | Comprehensive automated test coverage |


## Clinical methodology


### ESI decision tree

The Emergency Severity Index (ESI) stratification follows a 4-step algorithm:

- **Step A (ESI 1)**: Immediate life-saving intervention needed (unresponsive
  AVPU 'U', SpO2 < 80%, SBP < 60 mmHg, HR < 30 bpm).
- **Step B (ESI 2)**: High-risk situation, altered mental status (AVPU 'V'/'P'),
  severe pain (>= 7/10), acute red flag trigger, or vital sign danger zone.
- **Step C & D (ESI 3–5)**: Resource-based stratification (0 resources = ESI 5,
  1 resource = ESI 4, >= 2 resources = ESI 3, with danger zone escalation to
  ESI 2).


### Physiological danger zones

Vital signs are evaluated against age-specific physiological boundaries:

- **Neonate (0–28d)**: HR > 180 or < 100, RR > 50 or < 25, Temp > 38.0°C.
- **Infant (28d–3m)**: HR > 180 or < 90, RR > 50 or < 20, Temp > 38.0°C.
- **Toddler (3m–3y)**: HR > 160, RR > 40, SBP < 70 + (2 × age), Temp > 39.0°C.
- **Child (3–8y)**: HR > 140, RR > 30, SBP < 70 + (2 × age), Temp > 39.0°C.
- **Adult (8–65y)**: HR > 100 or < 50, RR > 20 or < 10, SBP < 90, Temp > 40.0°C.
- **Geriatric (65y+)**: HR > 90, RR > 20, SBP < 100, Temp < 36.0°C or > 38.0°C.


### Asymmetric safety escalation

To minimise preventable mortality from under-triage, the decision model
deliberately biases toward escalation: any case scoring ESI 3 with machine
learning confidence below 70%, or any identified red flag pattern, is
automatically escalated to ESI 2 for immediate physician evaluation.


### Red flag heuristics

The system detects four high-risk atypical presentations:

- **ATYPICAL_CARDIAC_FEMALE** — female aged 40+, complaint contains jaw pain,
  epigastric discomfort, nausea, fatigue, back pain, or indigestion.
- **GERIATRIC_SEPSIS** — age 65+, sepsis keywords, combined with hypothermia,
  hyperthermia, or elevated shock index.
- **PEDIATRIC_COMPENSATED_SHOCK** — age < 8, tachycardia above age threshold,
  yet systolic BP still normal (compensated phase).
- **SILENT_MI_DIABETIC** — diabetic patient with diaphoresis or dyspnea but
  no complaint of chest pain.


## Dataset

This project is built and validated using the Triagegeist open dataset:

- **Source**: Triagegeist dataset by laitinenfredriksson on Kaggle.
- **Foundations**: Statistically modelled from MIMIC-IV-ED and NHAMCS cohorts.
- **Records**: 100,000 anonymised emergency department patient encounters.

Download instructions are provided in [data/README.md](data/README.md).

The application includes 21 built-in demo patients covering all required
prototype diversity criteria (pediatric, geriatric, atypical cardiac,
ambiguous presentation, zero-history) and seeds them automatically on first
launch without requiring the dataset download.


## ML model training

The Hybrid Risk Scorer combines deterministic clinical rules with a trained
Random Forest classifier. Without a trained model the system falls back to
rules-only scoring (confidence 0.70). To enable ML scoring:

1. Download the Triagegeist dataset to `data/` (see [data/README.md](data/README.md)).
1. Run the training script:
    ```bash
    .venv\Scripts\python train_model.py    # Windows
    # python train_model.py               # macOS/Linux
    ```
1. The trained model is saved to `data/triage_model.joblib` and loaded
   automatically on the next application start.


## Safety & compliance

- **Non-device clinical decision support**: PatientTriage.ai is designed
  consistent with FDA Non-Device CDS guidance and Section 520(o)(1)(E) of the
  FD&C Act. The software presents clinical rationale, source vital parameters,
  and score breakdowns, leaving full decision authority with licensed nurses.
- **HIPAA and data privacy**: All demo records are synthetic or de-identified.
  No Protected Health Information (PHI) is transmitted or stored.
- **Regulatory jurisdiction assumed**: United States (HIPAA). Audit log entries
  record clinician ID, override reason codes, free-text rationale notes, and
  dwell time to satisfy documentation requirements.
- **Disclaimer**: This tool is an academic prototype and is not certified for
  independent diagnostic or therapeutic clinical use.


## Testing

Run the full automated test suite covering clinical rules, risk scoring, queue
ranking, and end-to-end pipelines:

```bash
.venv\Scripts\python -m pytest tests/ -v    # Windows
# python -m pytest tests/ -v               # macOS/Linux
```

Expected result: **43 passed, 0 warnings**.


## Troubleshooting

- **Groq API key not set**: The application automatically detects a missing
  API key and falls back to the deterministic keyword heuristic engine. To
  enable LLM inference, set the `GROQ_API_KEY` environment variable.
- **Dataset file not found**: Download `train.csv` from Kaggle into `data/`
  as detailed in [data/README.md](data/README.md). The built-in demo cohort
  is seeded automatically and does not require the dataset.
- **Speech-to-text not available**: The STT module is a stub. The recorder
  widget displays a warning and leaves the Chief Complaint field editable.
  To enable transcription, install `faster-whisper` and implement
  `src/stt_engine.py`.
- **ML model not found**: Run `train_model.py` after downloading the dataset.
  Without the model the system operates in rules-only mode.


## Maintainers

- Aagaman Pokhrel - [AgroKING](https://github.com/AgroKING)
- Abhinav Rijal - [abhinavrijal0-p](https://github.com/abhinavrijal0-p)
- Kritan Lamichhane -[kritanlamichhane](https://github.com/kritanlamichhane)
