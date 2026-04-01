from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_CUTTING_SPEED, DEFAULT_TAYLOR_C, DEFAULT_TAYLOR_N
from forge.physics.taylor_engine import TaylorPhysicsEngine


def main() -> None:
    engine = TaylorPhysicsEngine(
        mode="live",
        cutting_speed=DEFAULT_CUTTING_SPEED,
        material_n=DEFAULT_TAYLOR_N,
        material_C=DEFAULT_TAYLOR_C,
    )

    result = None
    for stroke in range(25):
        expected = engine.predict_features_at_stroke(stroke)
        actual = {
            "rms": expected["rms"] * (3.0 if stroke >= 20 else 1.0),
            "kurtosis": expected["kurtosis"] * (3.0 if stroke >= 20 else 1.0),
            "spectral_centroid": expected["spectral_centroid"] * (3.0 if stroke >= 20 else 1.0),
            "high_low_ratio": expected["high_low_ratio"] * (3.0 if stroke >= 20 else 1.0),
        }
        result = engine.compare_to_reality(actual, stroke)

    assert result is not None
    assert "divergence" in result
    assert "alert" in result
    assert "alert_level" in result
    assert "expected" in result
    assert "actual" in result
    assert result["divergence"] > 2.0
    print("Physics live-mode acceptance test passed")
    print(result)


if __name__ == "__main__":
    main()
