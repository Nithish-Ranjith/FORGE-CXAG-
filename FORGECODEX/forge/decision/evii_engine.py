from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    COMPLETE_JOB_ACTION,
    DOWNTIME_RATE_INR_PER_HOUR,
    PLANNED_REPLACE_HOURS,
    REPLACE_NOW_ACTION,
    RUN_TO_FAILURE_ACTION,
    STROKES_PER_HOUR,
    TOOL_COST_INR,
    UNPLANNED_DOWNTIME_HOURS,
)


class EVIIDecisionEngine:
    def __init__(self) -> None:
        self.tool_cost = TOOL_COST_INR
        self.downtime_rate = DOWNTIME_RATE_INR_PER_HOUR
        self.planned_replace_hours = PLANNED_REPLACE_HOURS
        self.unplanned_downtime_hours = UNPLANNED_DOWNTIME_HOURS
        self.strokes_per_hour = STROKES_PER_HOUR

    def compute(self, prediction: dict, current_job_strokes_remaining: int) -> dict:
        lower_bound, upper_bound = prediction.get("confidence_band", (0.0, 0.0))
        failure_probability = float(prediction.get("failure_probability", 0.0))
        cost_a = self.tool_cost + (self.planned_replace_hours * self.downtime_rate)

        if current_job_strokes_remaining > lower_bound:
            failure_cost = self.tool_cost + (self.unplanned_downtime_hours * self.downtime_rate)
            cost_b = (failure_probability * failure_cost) + ((1.0 - failure_probability) * self.tool_cost)
        else:
            cost_b = self.tool_cost

        cost_c = failure_probability * (
            self.tool_cost + (self.unplanned_downtime_hours * self.downtime_rate)
        )

        all_costs = {
            REPLACE_NOW_ACTION: float(cost_a),
            COMPLETE_JOB_ACTION: float(cost_b),
            RUN_TO_FAILURE_ACTION: float(cost_c),
        }
        optimal_action = min(all_costs, key=all_costs.get)
        worst_cost = max(all_costs.values())
        saving = float(worst_cost - all_costs[optimal_action])

        decision = {
            "optimal_action": optimal_action,
            "action_message": self._action_message(optimal_action, prediction, current_job_strokes_remaining),
            "saving_vs_worst": saving,
            "all_costs": all_costs,
            "failure_probability_pct": failure_probability * 100.0,
            "median_remaining_strokes": prediction.get("median_remaining_strokes", 0.0),
            "confidence_band": (lower_bound, upper_bound),
        }
        return decision

    def format_recommendation(self, decision: dict) -> str:
        costs = decision["all_costs"]
        return (
            f"FORGE Recommendation: {decision['action_message']}\n"
            f"Replace now cost: Rs. {costs[REPLACE_NOW_ACTION]:,.0f}\n"
            f"Complete job cost: Rs. {costs[COMPLETE_JOB_ACTION]:,.0f}\n"
            f"Run to failure cost: Rs. {costs[RUN_TO_FAILURE_ACTION]:,.0f}\n"
            f"*Expected saving*: Rs. {decision['saving_vs_worst']:,.0f}"
        )

    def _action_message(self, optimal_action: str, prediction: dict, current_job_strokes_remaining: int) -> str:
        median_strokes = float(prediction.get("median_remaining_strokes", 0.0))
        remaining_hours = median_strokes / self.strokes_per_hour if self.strokes_per_hour else 0.0
        if optimal_action == REPLACE_NOW_ACTION:
            return f"Replace now to avoid unplanned stoppage. Estimated safe life is {median_strokes:.0f} strokes (~{remaining_hours:.1f} hours)."
        if optimal_action == COMPLETE_JOB_ACTION:
            return (
                f"Complete the current job ({current_job_strokes_remaining} strokes remaining) and replace immediately after."
            )
        return "Run to failure is financially preferred under the current probability estimate."
