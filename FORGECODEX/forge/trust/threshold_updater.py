from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    ALERT_FAILURE_PROB_THRESHOLD,
    ALERT_RECALIBRATION_OVERRIDE_COUNT,
    ALERT_THRESHOLD_MAX,
    ALERT_THRESHOLD_MIN,
    ALERT_THRESHOLD_STEP,
)


class AdaptiveThresholdUpdater:
    def __init__(self, db) -> None:
        self.db = db
        self.current_threshold = ALERT_FAILURE_PROB_THRESHOLD

    def check_recalibration_needed(self, machine_id: str) -> float:
        overrides = self.db.get_recent_overrides(machine_id)
        unclear_count = sum(1 for row in overrides if row.get("reason_code") == 3)
        deadline_count = sum(1 for row in overrides if row.get("reason_code") == 2)

        old_threshold = self.current_threshold
        if unclear_count >= ALERT_RECALIBRATION_OVERRIDE_COUNT:
            self.current_threshold = min(ALERT_THRESHOLD_MAX, self.current_threshold + ALERT_THRESHOLD_STEP)
            reason = "Raised threshold due to repeated unclear overrides"
        elif deadline_count >= ALERT_RECALIBRATION_OVERRIDE_COUNT:
            self.current_threshold = max(ALERT_THRESHOLD_MIN, self.current_threshold - ALERT_THRESHOLD_STEP)
            reason = "Lowered threshold due to repeated deadline overrides"
        else:
            return self.current_threshold

        self.db.log_threshold_change(machine_id, old_threshold, self.current_threshold, reason)
        return self.current_threshold
