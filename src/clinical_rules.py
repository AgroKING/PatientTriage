import config
from src.models import Patient, VitalSigns


def get_age_group(age_years: float) -> str:
    for group, (low, high) in config.AGE_GROUPS.items():
        if group == "GERIATRIC":
            if age_years >= low:
                return group
        elif low <= age_years < high:
            return group
    return "ADULT"


def get_pediatric_sbp_threshold(age_years: float) -> int:
    return 70 + int(2 * age_years)


def check_danger_zone(vitals: VitalSigns, age_years: float) -> tuple[bool, list[str]]:
    group = get_age_group(age_years)
    thresholds = config.DANGER_ZONES[group]
    triggers: list[str] = []

    hr_high = thresholds.get("hr_high")
    if hr_high is not None and vitals.heart_rate > hr_high:
        triggers.append(f"HR {vitals.heart_rate} > {hr_high}")

    hr_low = thresholds.get("hr_low")
    if hr_low is not None and vitals.heart_rate < hr_low:
        triggers.append(f"HR {vitals.heart_rate} < {hr_low}")

    rr_high = thresholds.get("rr_high")
    if rr_high is not None and vitals.respiratory_rate > rr_high:
        triggers.append(f"RR {vitals.respiratory_rate} > {rr_high}")

    rr_low = thresholds.get("rr_low")
    if rr_low is not None and vitals.respiratory_rate < rr_low:
        triggers.append(f"RR {vitals.respiratory_rate} < {rr_low}")

    spo2_low = thresholds.get("spo2_low")
    if spo2_low is not None and vitals.spo2 < spo2_low:
        triggers.append(f"SpO2 {vitals.spo2}% < {spo2_low}%")

    sbp_low = thresholds.get("sbp_low")
    if group in ("TODDLER", "CHILD"):
        sbp_low = get_pediatric_sbp_threshold(age_years)
    if sbp_low is not None and vitals.systolic_bp < sbp_low:
        triggers.append(f"SBP {vitals.systolic_bp} < {sbp_low}")

    temp_high = thresholds.get("temp_high")
    if temp_high is not None and vitals.temperature > temp_high:
        triggers.append(f"Temp {vitals.temperature}°C > {temp_high}°C")

    temp_low = thresholds.get("temp_low")
    if temp_low is not None and vitals.temperature < temp_low:
        triggers.append(f"Temp {vitals.temperature}°C < {temp_low}°C")

    return (len(triggers) > 0, triggers)


def calculate_news2(vitals: VitalSigns) -> tuple[int, dict[str, int]]:
    def lookup_range_score(val: float, table: list[tuple[float, float, int]]) -> int:
        for low, high, score in table:
            if low <= val <= high:
                return score
        return 0

    rr_score = lookup_range_score(vitals.respiratory_rate, config.NEWS2_RR)
    spo2_score = lookup_range_score(vitals.spo2, config.NEWS2_SPO2)
    sbp_score = lookup_range_score(vitals.systolic_bp, config.NEWS2_SBP)
    hr_score = lookup_range_score(vitals.heart_rate, config.NEWS2_HR)
    temp_score = lookup_range_score(vitals.temperature, config.NEWS2_TEMP)
    consciousness_score = config.NEWS2_CONSCIOUSNESS.get(vitals.consciousness, 0)
    o2_score = 2 if vitals.supplemental_o2 else 0

    total = rr_score + spo2_score + sbp_score + hr_score + temp_score + consciousness_score + o2_score
    breakdown = {
        "rr": rr_score,
        "spo2": spo2_score,
        "sbp": sbp_score,
        "hr": hr_score,
        "temp": temp_score,
        "consciousness": consciousness_score,
        "o2": o2_score,
    }
    return total, breakdown


def calculate_shock_index(heart_rate: int, systolic_bp: int) -> tuple[float, bool]:
    if systolic_bp <= 0:
        return (99.99, True)
    si = heart_rate / systolic_bp
    return (round(si, 2), si > 0.85)


def check_red_flags(
    chief_complaint: str,
    age: float,
    sex: str,
    vitals: VitalSigns,
    has_diabetes: bool = False,
) -> list[str]:
    flags: list[str] = []
    complaint_lower = chief_complaint.lower()

    if sex == "F" and age >= 40:
        if any(keyword in complaint_lower for keyword in config.CARDIAC_FEMALE_KEYWORDS):
            flags.append("ATYPICAL_CARDIAC_FEMALE")

    if age >= 65:
        has_sepsis_kw = any(keyword in complaint_lower for keyword in config.SEPSIS_KEYWORDS)
        si_val, si_high = calculate_shock_index(vitals.heart_rate, vitals.systolic_bp)
        if has_sepsis_kw and (vitals.temperature < 36.0 or vitals.temperature > 38.0 or si_high):
            flags.append("GERIATRIC_SEPSIS")

    if age < 8:
        age_group = get_age_group(age)
        hr_high = config.DANGER_ZONES[age_group].get("hr_high", 140)
        ped_sbp_low = get_pediatric_sbp_threshold(age) if age >= 1 else (config.DANGER_ZONES[age_group].get("sbp_low") or 60)
        if vitals.heart_rate > hr_high and vitals.systolic_bp >= ped_sbp_low:
            flags.append("PEDIATRIC_COMPENSATED_SHOCK")

    if has_diabetes:
        sweat_dyspnea = any(k in complaint_lower for k in ["diaphoresis", "sweating", "dyspnea", "shortness of breath"])
        if sweat_dyspnea and "chest pain" not in complaint_lower:
            flags.append("SILENT_MI_DIABETIC")

    return flags


def generate_justification(
    esi: int,
    red_flags: list[str],
    danger_triggers: list[str],
    vitals: VitalSigns,
    patient: Patient | None = None,
) -> str:
    age_str = f"{int(patient.age)}" if patient else "adult"
    sex_str = patient.sex if patient else "patient"

    if "ATYPICAL_CARDIAC_FEMALE" in red_flags:
        justification = f"Atypical cardiac: {patient.chief_complaint if patient else 'symptoms'} in {age_str}{sex_str}"
    elif "GERIATRIC_SEPSIS" in red_flags:
        justification = f"Sepsis risk: temp {vitals.temperature} + altered mental + age {age_str}"
    elif "SILENT_MI_DIABETIC" in red_flags:
        justification = "Silent MI risk: diabetic diaphoresis/dyspnea without chest pain"
    elif "PEDIATRIC_COMPENSATED_SHOCK" in red_flags:
        justification = f"Pediatric shock: tachycardia HR {vitals.heart_rate} with normal BP"
    elif danger_triggers:
        top_triggers = " + ".join(danger_triggers[:2])
        justification = f"Danger zone vitals: {top_triggers}"
    elif esi == 1:
        justification = "Critical: immediate life-saving intervention required"
    else:
        justification = f"ESI {esi} based on clinical rules and vitals"

    words = justification.split()
    return " ".join(words[:10])


def esi_decision_tree(
    patient: Patient,
    vitals: VitalSigns,
    resources_needed: int,
    danger_zone_result: tuple[bool, list[str]],
    red_flags: list[str],
) -> tuple[int, str]:
    # Step A: Immediate life threat
    if vitals.consciousness == "U" or vitals.spo2 < 80 or vitals.systolic_bp < 60 or vitals.heart_rate < 30:
        return (1, "Immediate life-saving intervention required")

    # Step B: High risk situation / severe pain / red flags / danger zone
    if (
        vitals.consciousness in ("V", "P")
        or vitals.pain_score >= 7
        or len(red_flags) > 0
        or danger_zone_result[0]
    ):
        return (2, generate_justification(2, red_flags, danger_zone_result[1], vitals, patient))

    # Step C: Resource prediction
    if resources_needed == 0:
        return (5, "No resources needed")
    elif resources_needed == 1:
        return (4, "Single resource needed")
    else:
        # Step D: Vital sign danger zone check for resource >= 2
        if danger_zone_result[0]:
            return (2, generate_justification(2, red_flags, danger_zone_result[1], vitals, patient))
        else:
            return (3, "Stable, multiple resources needed")
