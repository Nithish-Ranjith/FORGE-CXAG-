from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from forge.prediction.train_tft import train_and_save


def main() -> None:
    saved_path = train_and_save()
    print(f"Saved checkpoint to {saved_path}")


if __name__ == "__main__":
    main()
