from pathlib import Path
import sys

import numpy as np
import pandas as pd

from config import (
    CALIBRATION_FACTOR_MAX,
    CALIBRATION_FACTOR_MIN,
    DEFAULT_CUTTING_SPEED,
    DEFAULT_TAYLOR_C,
    DEFAULT_TAYLOR_N,
    EPSILON,
    TRAINING_N_MAX,
    TRAINING_N_MIN,
    TRAINING_NOISE_MAX,
    TRAINING_NOISE_MIN,
    TRAINING_SPEED_MAX,
    TRAINING_SPEED_MIN,
    TRAINING_STROKES_MAX,
    TRAINING_STROKES_MIN,
    TWIN_DIVERGENCE_ALERT,
    TWIN_DIVERGENCE_CRITICAL,
    TWIN_DIVERGENCE_WARN,
    WEAR_EXPONENT,
)


class TaylorPhysicsEngine:
    def __init__(
        self,
        mode: str,
        cutting_speed: float = DEFAULT_CUTTING_SPEED,
        material_n: float = DEFAULT_TAYLOR_N,
        material_C: float = DEFAULT_TAYLOR_C,
    ) -> None:
        self.mode = mode
        self.cutting_speed = cutting_speed
        self.n = material_n
        self.C = material_C
        self.expected_tool_life = (self.C / self.cutting_speed) ** (1.0 / self.n)
        self.feature_history: list[dict[str, float]] = []
        self.baseline_mean: dict[str, float] | None = None
        self.baseline_std: dict[str, float] | None = None

    def predict_features_at_stroke(self, stroke_num: int) -> dict[str, float]:
        wear_pct = min(1.0, (float(stroke_num) / max(self.expected_tool_life, EPSILON)) ** WEAR_EXPONENT)
        expected = {
            "wear_pct": wear_pct,
            "remaining_life": max(0.0, self.expected_tool_life - float(stroke_num)),
            "rms": 0.012 + (0.038 * wear_pct),
            "kurtosis": 2.7 + (3.1 * wear_pct),
            "spectral_centroid": 3000.0 + (3600.0 * wear_pct),
            "high_low_ratio": 0.05 + (0.55 * wear_pct),
            "crest_factor": 3.2 + (3.8 * wear_pct),
            "peak_amplitude": 0.08 + (0.20 * wear_pct),
            "spectral_bandwidth": 900.0 + (1800.0 * wear_pct),
            "low_band_energy": max(0.1, 0.62 - (0.18 * wear_pct)),
            "mid_band_energy": 0.20 + (0.10 * wear_pct),
            "high_band_energy": 0.03 + (0.10 * wear_pct),
            "dominant_freq": 1200.0 + (7200.0 * wear_pct),
            "biometric_wear": min(1.0, 0.45 * wear_pct),
            "twin_divergence": min(4.0, 0.8 + (2.8 * wear_pct)),
            "cutting_speed": self.cutting_speed,
        }
        return expected

    def generate_training_dataset(self, n_tools: int, output_path: str) -> pd.DataFrame:
        if self.mode != "offline":
            raise ValueError("generate_training_dataset is available only in offline mode")
        records: list[dict[str, float | int | str]] = []
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        for tool_index in range(n_tools):
            speed = float(np.random.uniform(TRAINING_SPEED_MIN, TRAINING_SPEED_MAX))
            material_n = float(np.random.uniform(TRAINING_N_MIN, TRAINING_N_MAX))
            total_strokes = int(np.random.uniform(TRAINING_STROKES_MIN, TRAINING_STROKES_MAX))
            noise_scale = float(np.random.uniform(TRAINING_NOISE_MIN, TRAINING_NOISE_MAX))
            tool_id = f"tool_{tool_index:03d}"

            tool_engine = TaylorPhysicsEngine("offline", speed, material_n, self.C)
            for stroke in range(total_strokes):
                expected = tool_engine.predict_features_at_stroke(stroke)
                records.append(
                    {
                        "tool_id": tool_id,
                        "stroke": stroke,
                        "wear_pct": expected["wear_pct"],
                        "remaining_life": max(0.0, float(total_strokes - stroke)),
                        "rms": self._noisy_feature(expected["rms"], noise_scale),
                        "kurtosis": self._noisy_feature(expected["kurtosis"], noise_scale),
                        "spectral_centroid": self._noisy_feature(expected["spectral_centroid"], noise_scale),
                        "high_low_ratio": self._noisy_feature(expected["high_low_ratio"], noise_scale),
                        "crest_factor": self._noisy_feature(expected["crest_factor"], noise_scale),
                        "biometric_wear": self._noisy_feature(expected["biometric_wear"], noise_scale),
                        "twin_divergence": self._noisy_feature(expected["twin_divergence"], noise_scale),
                        "cutting_speed": speed,
                    }
                )

        dataset = pd.DataFrame(records)
        dataset.to_csv(output, index=False)
        return dataset

    def compare_to_reality(self, actual_features: dict[str, float], stroke_num: int) -> dict:
        if self.mode != "live":
            raise ValueError("compare_to_reality is available only in live mode")
        expected = self.predict_features_at_stroke(stroke_num)
        tracked_keys = ["rms", "kurtosis", "spectral_centroid", "high_low_ratio"]
        self.feature_history.append({key: float(actual_features.get(key, 0.0)) for key in tracked_keys})

        if stroke_num < 20:
            return {
                "status": "building_baseline",
                "divergence": 0.0,
                "alert": False,
                "alert_level": "BASELINE",
                "expected": expected,
                "actual": actual_features,
                "message": "Building baseline",
            }

        if stroke_num == 20 or self.baseline_mean is None or self.baseline_std is None:
            baseline_frame = pd.DataFrame(self.feature_history[:20])
            self.baseline_mean = baseline_frame.mean().to_dict()
            self.baseline_std = baseline_frame.std(ddof=0).replace(0.0, EPSILON).to_dict()

        z_scores = []
        for key in tracked_keys:
            mean_value = float(self.baseline_mean.get(key, 0.0))
            std_value = max(float(self.baseline_std.get(key, EPSILON)), EPSILON)
            expected_value = float(expected.get(key, mean_value))
            actual_value = float(actual_features.get(key, 0.0))
            z_score = abs(actual_value - expected_value) / std_value
            z_scores.append(z_score)

        mean_divergence = float(np.mean(z_scores))
        alert_level = "NORMAL"
        if mean_divergence > TWIN_DIVERGENCE_CRITICAL:
            alert_level = "CRITICAL"
        elif mean_divergence > TWIN_DIVERGENCE_ALERT:
            alert_level = "WARNING"
        elif mean_divergence > TWIN_DIVERGENCE_WARN:
            alert_level = "WATCH"

        return {
            "divergence": mean_divergence,
            "alert": alert_level in {"WATCH", "WARNING", "CRITICAL"},
            "alert_level": alert_level,
            "expected": expected,
            "actual": actual_features,
            "message": f"Divergence at {mean_divergence:.2f} sigma",
        }

    def calibrate_to_tool(self, calibration_factor: float) -> None:
        if CALIBRATION_FACTOR_MIN <= calibration_factor <= CALIBRATION_FACTOR_MAX:
            self.C = self.C * calibration_factor
            self.expected_tool_life = (self.C / self.cutting_speed) ** (1.0 / self.n)
            return
        print("TaylorPhysicsEngine calibration factor out of range; keeping default", file=sys.stderr)

    def _noisy_feature(self, baseline_value: float, noise_scale: float) -> float:
        noisy_value = baseline_value + np.random.normal(0.0, max(abs(baseline_value), 1.0) * noise_scale)
        return float(max(0.0, noisy_value))
