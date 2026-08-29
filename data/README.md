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
