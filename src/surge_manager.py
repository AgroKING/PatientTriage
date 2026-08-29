class SurgeManager:
    def __init__(self) -> None:
        self.active: bool = False
        self.categories: dict[str, list[str]] = {
            "RED": [],
            "YELLOW": [],
            "GREEN": [],
            "BLUE": [],
        }

    def activate(self) -> None:
        self.active = True
        self.categories = {"RED": [], "YELLOW": [], "GREEN": [], "BLUE": []}

    def deactivate(self) -> None:
        self.active = False
        self.categories = {"RED": [], "YELLOW": [], "GREEN": [], "BLUE": []}

    def is_active(self) -> bool:
        return self.active

    def start_triage(
        self,
        patient_id: str,
        can_walk: bool,
        respiratory_rate: int | None,
        has_radial_pulse: bool,
        follows_commands: bool,
        breathing_after_airway: bool,
    ) -> str:
        if can_walk:
            category = "GREEN"
        elif respiratory_rate is None or respiratory_rate == 0:
            if not breathing_after_airway:
                category = "BLUE"
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

        # Remove patient from previous category if present
        for cat in self.categories.values():
            if patient_id in cat:
                cat.remove(patient_id)

        self.categories[category].append(patient_id)
        return category

    def _migrate(self) -> None:
        if "BLACK" in self.categories:
            black_pts = self.categories.pop("BLACK", [])
            if "BLUE" not in self.categories:
                self.categories["BLUE"] = []
            self.categories["BLUE"].extend(black_pts)

    def get_stats(self) -> dict[str, int]:
        self._migrate()
        return {cat: len(patients) for cat, patients in self.categories.items()}

    def get_all_categorized(self) -> dict[str, list[str]]:
        self._migrate()
        return self.categories
