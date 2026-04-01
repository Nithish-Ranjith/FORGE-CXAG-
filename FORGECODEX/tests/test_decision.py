from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_CUTTING_SPEED, DEFAULT_TAYLOR_C, DEFAULT_TAYLOR_N
from forge.biometrics.tool_fingerprint import ToolBiometrics
from forge.decision.evii_engine import EVIIDecisionEngine
from forge.physics.taylor_engine import TaylorPhysicsEngine


def make_sine_wave(
    freq_hz: float,
    amplitude: float = 0.1,
    sample_rate: int = 44100,
    duration_sec: float = 0.5,
) -> np.ndarray:
    sample_count = int(sample_rate * duration_sec)
    time_axis = np.arange(sample_count, dtype=np.float32) / np.float32(sample_rate)
    return np.float32(amplitude) * np.sin(np.float32(2.0 * np.pi * freq_hz) * time_axis)


def test_biometrics() -> None:
    physics_engine = TaylorPhysicsEngine(
        mode="live",
        cutting_speed=DEFAULT_CUTTING_SPEED,
        material_n=DEFAULT_TAYLOR_N,
        material_C=DEFAULT_TAYLOR_C,
    )
    biometrics = ToolBiometrics("BROACH-HSS-001", physics_engine)
    baseline_wave = make_sine_wave(1000.0, amplitude=0.021)

    result = None
    for _ in range(20):
        result = biometrics.enroll_stroke(baseline_wave)

    assert result == "enrolled"
    assert biometrics.calibrated is True

    same_wave_distance = biometrics.measure_wear_distance(baseline_wave)
    different_wave_distance = biometrics.measure_wear_distance(make_sine_wave(5000.0, amplitude=0.021))

    assert same_wave_distance < 0.05
    assert different_wave_distance > 0.3


def test_decision_engine() -> None:
    engine = EVIIDecisionEngine()
    prediction = {
        "failure_probability": 0.8,
        "median_remaining_strokes": 30,
        "confidence_band": (30, 60),
    }
    decision = engine.compute(prediction, current_job_strokes_remaining=80)

    assert decision["all_costs"]["COMPLETE_JOB_THEN_REPLACE"] > decision["all_costs"]["REPLACE_NOW"]
    assert decision["saving_vs_worst"] > 0
    for key in [
        "optimal_action",
        "action_message",
        "saving_vs_worst",
        "all_costs",
        "failure_probability_pct",
    ]:
        assert key in decision


def main() -> None:
    test_biometrics()
    test_decision_engine()
    print("Day 4 acceptance tests passed")


if __name__ == "__main__":
    main()
