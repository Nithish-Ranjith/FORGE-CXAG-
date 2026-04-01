from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_CUTTING_SPEED,
    DEFAULT_TAYLOR_C,
    DEFAULT_TAYLOR_N,
    TRAINING_DATA_PATH,
    TRAINING_MIN_ROWS,
    TRAINING_TOOL_COUNT,
)
from forge.physics.taylor_engine import TaylorPhysicsEngine


def main() -> None:
    engine = TaylorPhysicsEngine(
        mode="offline",
        cutting_speed=DEFAULT_CUTTING_SPEED,
        material_n=DEFAULT_TAYLOR_N,
        material_C=DEFAULT_TAYLOR_C,
    )
    dataset = engine.generate_training_dataset(TRAINING_TOOL_COUNT, TRAINING_DATA_PATH)

    required_columns = {
        "tool_id",
        "stroke",
        "wear_pct",
        "remaining_life",
        "rms",
        "kurtosis",
        "spectral_centroid",
        "high_low_ratio",
        "crest_factor",
        "cutting_speed",
    }
    missing_columns = required_columns.difference(dataset.columns)
    if missing_columns:
        raise RuntimeError(f"Missing required columns: {sorted(missing_columns)}")
    if len(dataset) < TRAINING_MIN_ROWS:
        raise RuntimeError(f"Dataset row count too low: {len(dataset)}")

    print(f"Generated {len(dataset)} rows across {dataset['tool_id'].nunique()} tool lifetimes")
    print(f"Saved dataset to {TRAINING_DATA_PATH}")


if __name__ == "__main__":
    main()
