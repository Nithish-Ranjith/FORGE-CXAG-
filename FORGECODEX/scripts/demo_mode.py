from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import TRAINING_DATA_PATH


def main() -> None:
    output_path = Path("data/demo_mode_stream.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    max_iterations = 50000
    with output_path.open("w", encoding="utf-8") as handle:
        for iteration in range(max_iterations + 1):
            wear_pct = min(95.0, (95.0 * iteration) / max_iterations)
            payload = {
                "iteration": iteration,
                "wear_pct": wear_pct,
                "alert_triggered": wear_pct >= 75.0,
                "source_training_data": TRAINING_DATA_PATH,
            }
            handle.write(json.dumps(payload) + "\n")
    print(f"Generated {max_iterations + 1} demo iterations at {output_path}")


if __name__ == "__main__":
    main()
