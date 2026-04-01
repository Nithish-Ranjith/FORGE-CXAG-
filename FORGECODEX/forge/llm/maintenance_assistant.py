from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    LLM_MAX_TOKENS,
    OVERRIDE_REASON_TEXT,
    TAMIL_UNICODE_MAX,
    TAMIL_UNICODE_MIN,
)

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


class FORGEMaintenanceAI:
    def __init__(self, machine_id: str, db) -> None:
        self.client = None
        if anthropic and ANTHROPIC_API_KEY:
            try:
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except Exception:
                self.client = None
        self.conversation_history: list[dict[str, str]] = []
        self.machine_id = machine_id
        self.db = db

    def ask(self, operator_message: str, forge_state: dict) -> str:
        system_prompt = self._build_system_prompt(forge_state)
        self.conversation_history.append({"role": "user", "content": operator_message})

        if self._contains_override_keyword(operator_message):
            self._prompt_override_reason()

        if self.client is not None:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                system=system_prompt,
                messages=self.conversation_history,
            )
            response_text = "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            )
        else:
            response_text = self._offline_response(operator_message, forge_state)

        self.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    def _build_system_prompt(self, forge_state: dict) -> str:
        feature_values = forge_state.get("features", {})
        prediction = forge_state.get("prediction", {})
        decision = forge_state.get("decision", {})
        twin = forge_state.get("twin_result", {})
        overrides = self.db.get_recent_overrides(self.machine_id, days=30)[:3]
        similar = self.db.find_similar_patterns(self.machine_id, float(feature_values.get("kurtosis", 0.0)))
        return (
            f"Machine ID: {self.machine_id}\n"
            f"Features: {feature_values}\n"
            f"Prediction: {prediction}\n"
            f"Decision: {decision}\n"
            f"Digital Twin: {twin}\n"
            f"Recent Overrides: {overrides}\n"
            f"Similar Past Events: {similar}\n"
            "Detect operator language and respond in the same language. Maximum 3 sentences unless detail requested."
        )

    def reset_conversation(self) -> None:
        self.conversation_history = []

    def _offline_response(self, operator_message: str, forge_state: dict) -> str:
        prediction = forge_state.get("prediction", {})
        decision = forge_state.get("decision", {})
        features = forge_state.get("features", {})
        tamil = self._is_tamil(operator_message)
        kurtosis_value = features.get("kurtosis", 0.0)
        remaining = prediction.get("median_remaining_strokes", 0.0)
        saving = decision.get("saving_vs_worst", 0.0)
        if tamil:
            return (
                f"Machine {self.machine_id} இப்போது kurtosis {kurtosis_value:.2f} ஆக உள்ளது. "
                f"மீதமுள்ள ஆயுள் சுமார் {remaining:.0f} strokes, சேமிப்பு சுமார் Rs. {saving:,.0f}."
            )
        return (
            f"Machine {self.machine_id} is alerting because kurtosis is {kurtosis_value:.2f}. "
            f"Estimated remaining life is {remaining:.0f} strokes and the current recommendation saves about Rs. {saving:,.0f}."
        )

    def _contains_override_keyword(self, operator_message: str) -> bool:
        lowered = operator_message.lower()
        return "override" in lowered or "ignore" in lowered

    def _prompt_override_reason(self) -> str:
        return "Please choose an override reason: " + ", ".join(
            f"[{code}] {text}" for code, text in OVERRIDE_REASON_TEXT.items()
        )

    def _is_tamil(self, text: str) -> bool:
        return any(TAMIL_UNICODE_MIN <= ord(char) <= TAMIL_UNICODE_MAX for char in text)
