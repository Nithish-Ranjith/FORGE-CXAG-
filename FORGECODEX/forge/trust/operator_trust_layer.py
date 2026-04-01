from pathlib import Path
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    OVERRIDE_REASON_TEXT,
    STROKES_PER_HOUR,
    TRUST_EXPLANATION_TEMPLATES,
    TRUST_FEATURE_NAME_MAP,
)


class _NoOpThresholdUpdater:
    def check_recalibration_needed(self, machine_id: str) -> None:
        return None


class OperatorTrustLayer:
    def __init__(self, db, tool_id: str, threshold_updater=None) -> None:
        self.db = db
        self.tool_id = tool_id
        self.threshold_updater = threshold_updater or _NoOpThresholdUpdater()
        self.redesign_flags: list[str] = []

    def explain_prediction(self, feature_history_df: pd.DataFrame, prediction: dict, twin_result: dict) -> str:
        top_feature_name = self._resolve_top_feature_name(feature_history_df, prediction)
        explanation = TRUST_EXPLANATION_TEMPLATES.get(
            top_feature_name,
            "Multiple sensor patterns moved away from baseline at the same time.",
        )
        similar_patterns = self.db.find_similar_patterns(
            twin_result.get("machine_id", ""),
            float(feature_history_df["kurtosis"].iloc[-1]) if "kurtosis" in feature_history_df else 0.0,
        )
        if similar_patterns:
            precedent = similar_patterns[0]
            explanation += (
                f" Similar pattern seen on this machine before with alert level {precedent['alert_level']}."
            )
        return explanation

    def format_uncertainty(self, prediction: dict) -> dict[str, str]:
        lower_bound, upper_bound = prediction.get("confidence_band", (0.0, 0.0))
        median = float(prediction.get("median_remaining_strokes", 0.0))
        hours = median / STROKES_PER_HOUR if STROKES_PER_HOUR else 0.0
        failure_probability = float(prediction.get("failure_probability", 0.0)) * 100.0
        return {
            "primary": f"{median:.0f} strokes (~{hours:.1f} hours)",
            "range": f"80% confident: {lower_bound:.0f}–{upper_bound:.0f} strokes",
            "risk": f"{failure_probability:.0f}% failure chance before {lower_bound:.0f} strokes",
        }

    def compose_alert(
        self,
        machine_id: str,
        prediction: dict,
        decision: dict,
        twin_result: dict,
        feature_history_df: pd.DataFrame,
    ) -> tuple[str, str]:
        twin_result = dict(twin_result)
        twin_result["machine_id"] = machine_id
        explanation = self.explain_prediction(feature_history_df, prediction, twin_result)
        uncertainty = self.format_uncertainty(prediction)
        emoji = self._emoji_for_level(twin_result.get("alert_level", "WATCH"))
        message = (
            f"{emoji} FORGE ALERT — Machine {machine_id}\n\n"
            f"{explanation}\n\n"
            f"Remaining Life: {uncertainty['primary']}\n"
            f"Confidence: {uncertainty['range']}\n"
            f"Risk: {uncertainty['risk']}\n\n"
            f"RECOMMENDATION:\n"
            f"{decision['action_message']}\n\n"
            f"Expected saving: Rs. {decision['saving_vs_worst']:,.0f}\n\n"
            f"Physics Divergence: {float(twin_result.get('divergence', 0.0)):.1f} sigma\n\n"
            f"[Done] [Override] [Ask FORGE]"
        )
        alert_id = self.db.log_alert(
            machine_id,
            self.tool_id,
            int(feature_history_df["stroke_num"].iloc[-1]) if "stroke_num" in feature_history_df else 0,
            twin_result.get("alert_level", "WATCH"),
            message,
            decision,
        )
        return message, alert_id

    def record_override(self, alert_id: str, reason_code: int, machine_id: str) -> None:
        self.db.log_override(alert_id, machine_id, reason_code)
        if reason_code == 3:
            self._flag_alert_redesign(alert_id)
        self.threshold_updater.check_recalibration_needed(machine_id)

    def _resolve_top_feature_name(self, feature_history_df: pd.DataFrame, prediction: dict) -> str:
        if "top_feature_index" in prediction:
            return TRUST_FEATURE_NAME_MAP.get(int(prediction["top_feature_index"]), "kurtosis")
        if feature_history_df.empty:
            return "kurtosis"
        numeric_cols = [col for col in feature_history_df.columns if pd.api.types.is_numeric_dtype(feature_history_df[col])]
        if not numeric_cols:
            return "kurtosis"
        latest_row = feature_history_df[numeric_cols].iloc[-1].abs()
        return str(latest_row.idxmax())

    def _emoji_for_level(self, alert_level: str) -> str:
        return {"CRITICAL": "🔴", "WARNING": "🟠", "WATCH": "🟡"}.get(alert_level, "🟡")

    def _flag_alert_redesign(self, alert_id: str) -> None:
        self.redesign_flags.append(alert_id)
