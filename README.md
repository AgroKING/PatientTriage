# PatientTriage.ai

PatientTriage.ai is an intelligent clinical decision-support system designed
to assist emergency department (ED) triage nurses in accurately assigning
Emergency Severity Index (ESI) levels. By combining age-adjusted physiological
danger zones, the National Early Warning Score (NEWS2), targeted red-flag
clinical heuristics, and Large Language Model (LLM) complaint analysis, the
platform delivers rapid, transparent, and defensible triage recommendations
with high-confidence clinical justifications in under ten words.

In fast-paced, high-stress emergency environments, cognitive fatigue and
incomplete data often lead to catastrophic under-triage—such as overlooking
atypical cardiac presentations in women, silent myocardial infarctions in
diabetic patients, or compensated shock in pediatrics. PatientTriage.ai
addresses these challenges through asymmetric safety-first escalation, dynamic
waiting room priority re-ranking, immutable audit logging, and rapid 전환
into the START protocol during mass-casualty surges.

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
- Safety & compliance
- Testing
- Troubleshooting
- Maintainers


## Requirements

This project requires the following tools and services:

- Python 3.10 or higher
- [Groq API Key](https://console.groq.com/) for high-speed Llama-3 inference
  (optional; regex fallback active if omitted)
- Kaggle account to obtain the optional 100k Triagegeist dataset


## Installation

1. Clone the repository to your local workstation:
    ```bash
    git clone https://github.com/AgroKING/PatientTriage.git
    cd PatientTriage
    ```
1. Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```


## Configuration

1. Set up your Groq API key in your shell environment:
    ```bash
    export GROQ_API_KEY="gsk_your_groq_api_key_here"
    ```
1. Download the optional Triagegeist dataset following the instructions in
   [Dataset Documentation](data/README.md).
1. Initialize the SQLite database and seed initial test cohorts:
    ```bash
    python3 -c "import config, src.database as db; db.init_db(config.DB_PATH); print('Database initialized.')"
    ```


## Usage

Launch the multi-page Streamlit application with the following command:

```bash
streamlit run app.py
```

The application provides four operational modules accessible from the sidebar:

- **Patient intake**: Perform manual vitals and chief complaint intake or
  load pre-configured patient records from the database. View instant ESI
  scoring, confidence bars, NEWS2 breakdown, and clinician Accept/Override
  actions.
- **Live queue**: Monitor real-time dynamic queue rankings combining ESI
  acuity and waiting elapsed time with automatic deterioration alerts for
  overdue patients.
- **Audit log**: Review the tamper-evident, append-only audit trail capturing
  all AI suggestions, clinician overrides, reason codes, rationale notes, and
  decision dwell times, with one-click CSV export.
- **Surge mode**: Instantly toggle Simple Triage and Rapid Treatment (START)
  mass-casualty triage protocol and execute 3x volume emergency simulations
  with interactive Plotly distribution charts.


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
- **Toddler (3m–3y)**: HR > 160, RR > 40, SBP < 70 + (2 * age), Temp > 39.0°C.
- **Child (3–8y)**: HR > 140, RR > 30, SBP < 70 + (2 * age), Temp > 39.0°C.
- **Adult (8–65y)**: HR > 100 or < 50, RR > 20 or < 10, SBP < 90, Temp > 40.0°C.
- **Geriatric (65y+)**: HR > 90, RR > 20, SBP < 100, Temp < 36.0°C or > 38.0°C.

### Asymmetric safety escalation

To minimize preventable mortality from under-triage, the decision model
deliberately biases toward escalation: any case scoring ESI 3 with machine
learning confidence below 70% or any identified red flag pattern is
automatically escalated to ESI 2 for immediate physician evaluation.


## Dataset

This project is built and validated using the Triagegeist open dataset:

- **Source**: Triagegeist dataset by laitinenfredriksson on Kaggle.
- **Foundations**: Statistically modeled from MIMIC-IV-ED and NHAMCS cohorts.
- **Records**: 100,000 anonymized emergency department patient encounters.


## Safety & compliance

- **Non-device clinical decision support**: PatientTriage.ai is designed
  consistent with FDA Non-Device CDS guidance and Section 520(o)(1)(E) of the
  FD&C Act. The software presents clinical rationale, source vital parameters,
  and score breakdowns, leaving full decision authority with licensed nurses.
- **HIPAA and data privacy**: All demo records are synthetic or de-identified.
  No Protected Health Information (PHI) is transmitted or stored.
- **Disclaimer**: This tool is an academic prototype and is not certified for
  independent diagnostic or therapeutic clinical use.


## Testing

Run the full automated test suite covering clinical rules, risk scoring, queue
ranking, and end-to-end pipelines:

```bash
pytest tests/ -v
```


## Troubleshooting

- **Groq API key not set**: The application automatically detects missing API
  keys and falls back to the deterministic keyword heuristic engine. To enable
  LLM inference, export `GROQ_API_KEY`.
- **Dataset file not found**: Download `train.csv` from Kaggle into `data/` as
  detailed in [Dataset README](data/README.md), or use the built-in demo cohort
  generator.


## Maintainers

- Aagaman Pokhrel - [AgroKING](https://github.com/AgroKING)
