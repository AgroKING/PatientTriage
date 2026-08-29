import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import config
from src.clinical_rules import (
    calculate_news2,
    check_danger_zone,
    check_red_flags,
    esi_decision_tree,
)
from src.models import ComplaintAnalysis, Patient, TriageResult, VitalSigns


class HybridRiskScorer:
    def __init__(self, model_path: str | None = None) -> None:
        self.model = None
        self.feature_names = [
            "age", "sex_encoded", "heart_rate", "respiratory_rate",
            "spo2", "systolic_bp", "diastolic_bp", "temperature", "pain_score"
        ]
        if model_path and os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
            except Exception:
                self.model = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
        clf.fit(X, y)
        self.model = clf
        self.feature_names = X.columns.tolist()

    def save_model(self, path: str) -> None:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        if self.model is not None:
            joblib.dump(self.model, path)

    def score(
        self,
        patient: Patient,
        vitals: VitalSigns,
        complaint_analysis: ComplaintAnalysis,
        resources_needed: int,
    ) -> TriageResult:
        is_danger, triggers = check_danger_zone(vitals, patient.age)
        has_diabetes = "diabet" in patient.medical_history.lower()
        flags = check_red_flags(
            patient.chief_complaint,
            patient.age,
            patient.sex,
            vitals,
            has_diabetes=has_diabetes,
        )

        for rf in complaint_analysis.red_flags:
            if rf not in flags:
                flags.append(rf)

        rule_esi, rule_justification = esi_decision_tree(
            patient,
            vitals,
            resources_needed,
            (is_danger, triggers),
            flags,
        )

        news2_score, _ = calculate_news2(vitals)

        if self.model is not None:
            sex_enc = 1 if patient.sex == "F" else 0
            feat = pd.DataFrame(
                [[
                    patient.age,
                    sex_enc,
                    vitals.heart_rate,
                    vitals.respiratory_rate,
                    vitals.spo2,
                    vitals.systolic_bp,
                    vitals.diastolic_bp,
                    vitals.temperature,
                    vitals.pain_score,
                ]],
                columns=self.feature_names,
            )
            probs = self.model.predict_proba(feat)[0]
            ml_confidence = float(np.max(probs))
            best_idx = int(np.argmax(probs))
            ml_esi = int(self.model.classes_[best_idx])
        else:
            ml_confidence = 0.5
            ml_esi = rule_esi

        final_esi = rule_esi
        if ml_esi < final_esi:
            final_esi = ml_esi

        if (
            complaint_analysis.suggested_esi is not None
            and complaint_analysis.confidence > 0.7
            and complaint_analysis.suggested_esi < final_esi
        ):
            final_esi = complaint_analysis.suggested_esi

        # Asymmetric escalation: if final is ESI 3 and uncertain or flags triggered -> escalate to ESI 2
        if final_esi == 3 and (
            ml_confidence < config.CONFIDENCE_ESCALATION_THRESHOLD
            or len(flags) > 0
            or is_danger
        ):
            final_esi = 2

        # Step A guarantee: ESI 1 from rules never gets downgraded
        if rule_esi == 1:
            final_esi = 1

        rule_confidence = 0.9 if (is_danger or len(flags) > 0) else 0.7
        final_confidence = (
            0.5 * rule_confidence
            + 0.3 * ml_confidence
            + 0.2 * complaint_analysis.confidence
        )
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Select concise justification (max 10 words)
        if complaint_analysis.justification and complaint_analysis.confidence >= 0.7:
            justification = complaint_analysis.justification
        else:
            justification = rule_justification

        words = justification.split()
        justification = " ".join(words[:10])
        if not justification:
            justification = f"ESI {final_esi} based on clinical assessment"

        return TriageResult(
            patient_id=patient.id,
            esi_level=final_esi,
            news2_score=news2_score,
            confidence=round(final_confidence, 2),
            justification=justification,
            red_flags=flags,
        )

    def get_feature_importance(self) -> dict[str, float]:
        if self.model is not None and hasattr(self.model, "feature_importances_"):
            return {
                name: round(float(imp), 4)
                for name, imp in zip(self.feature_names, self.model.feature_importances_)
            }
        return {}
