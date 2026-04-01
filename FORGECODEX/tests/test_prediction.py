from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from forge.prediction.tft_predictor import FORGEPredictor


def main() -> None:
    predictor = FORGEPredictor("data/models/forge_tft_v1.ckpt")
    prediction = None
    for stroke in range(30):
        prediction = predictor.predict(
            {
                "tool_id": "tool_demo",
                "stroke_num": stroke,
                "stroke": stroke,
                "cutting_speed": 8.0,
                "rms": 0.01 + stroke * 0.0005,
                "kurtosis": 2.7 + stroke * 0.05,
                "spectral_centroid": 3000 + stroke * 50,
                "high_low_ratio": 0.05 + stroke * 0.01,
                "crest_factor": 3.2 + stroke * 0.05,
                "biometric_wear": min(1.0, stroke * 0.02),
                "twin_divergence": min(4.0, stroke * 0.04),
                "remaining_life": max(0, 500 - stroke * 10),
            }
        )
    assert prediction is not None
    lower_bound, upper_bound = prediction["confidence_band"]
    assert lower_bound < prediction["median_remaining_strokes"] < upper_bound
    assert prediction["failure_probability"] >= 0.6
    print("Prediction smoke test passed")
    print(prediction)


if __name__ == "__main__":
    main()
